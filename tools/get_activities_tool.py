from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import gradio as gr
from typing import Any, List, Tuple, Dict
from dotenv import load_dotenv
import psycopg2
from Azent.Azent import Agent
from openai import AzureOpenAI
import os
from opik.integrations.openai import track_openai
from opik import track

load_dotenv()


@track
def get_activities_by_activity_name(acitivity: str, location: str) -> List[str]:
    conn = psycopg2.connect(os.getenv("VECTOR_DB_URL"))
    cursor = conn.cursor()
    cursor = conn.cursor()

    print("location", location)
    openai_client = AzureOpenAI(
        api_key=os.getenv('OPENAI_API_KEY'),
        azure_deployment=os.getenv('AZURE_DEPLOYMENT'),
        azure_endpoint='gpt-4o-mvp-dev',
        azure_api_version='2024-02-15-preview'
    )

    response = openai_client.embeddings.create(
        input=[f"{acitivity} in {location}"],
        model="text-embedding-ada-002"
    )

    query_embedding = response.data[0].embedding
    query_vector_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    # get location id
    cursor.execute(f"SELECT id FROM destination WHERE name ILIKE '{location}'")
    row = cursor.fetchone()
    location_id = row[0]

    print("location_id", location_id)

    threshold = 0.5  # Set your desired threshold
    sql = """
            SELECT 
                id, 
                name, 
                description,
                activity_image_url,
                activity_duration,
                -(embedding <#> %s::vector) as similarity
            FROM must_travel_activity 
            WHERE 
                destination_id = %s 
                AND -(embedding <#> %s::vector) > 0.85  -- Cosine similarity threshold
            ORDER BY similarity DESC
            LIMIT 5;
        """

    cursor.execute(sql, (
        query_vector_str,
        location_id,
        query_vector_str
    ))

    rows = cursor.fetchall()
    activities = []

    for row in rows:
        print(row)
        activity_id = row[0]
        activity_name = row[1]
        activity_desc = row[2]
        distance = row[3]
        print(f"Activity: {activity_name}, Distance: {distance}")
        activities.append(activity_name)

    cursor.close()
    conn.close()
    return activities


@track
def get_activities_by_group_type(group_type: str, location: str) -> List[str]:
    conn = psycopg2.connect(os.getenv("VECTOR_DB_URL"))
    cursor = conn.cursor()

    print("group_type", group_type)
    openai_client = AzureOpenAI(
        api_key=os.getenv('OPENAI_API_KEY'),
        azure_deployment=os.getenv('AZURE_DEPLOYMENT'),
        azure_endpoint='gpt-4o-mvp-dev',
        azure_api_version='2024-02-15-preview'
    )

    response = openai_client.embeddings.create(
        input=[f"group_type: {group_type}"],
        model="text-embedding-ada-002"
    )

    query_embedding = response.data[0].embedding
    query_vector_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

    # get location id
    cursor.execute(f"SELECT id FROM destination WHERE name ILIKE '{location}'")
    row = cursor.fetchone()
    location_id = row[0]

    print("location_id", location_id)

    sql = """
        WITH matching_groups AS (
            SELECT 
                id,
                name,
                -(embedding <#> %s::vector) as similarity
            FROM travel_group
            WHERE -(embedding <#> %s::vector) > 0.85
            ORDER BY similarity DESC
            LIMIT 3
        )
        SELECT 
            mta.id,
            mta.name,
            mta.description,
            mtagt.rating,
            mg.name as group_name,
            mta.activity_image_url,
            mta.activity_duration,
            mg.similarity as group_similarity
        FROM must_travel_activity mta
        JOIN must_activity_group_theme mtagt ON mta.id = mtagt.must_travel_activity_id
        JOIN matching_groups mg ON mtagt.travel_group_id = mg.id
        WHERE mta.destination_id = %s
        ORDER BY mg.similarity DESC, mtagt.rating DESC
        LIMIT 5;
    """

    cursor.execute(sql, (
        query_vector_str,
        query_vector_str,
        location_id
    ))
    rows = cursor.fetchall()
    activities = []

    for row in rows:
        id_ = row[0]
        activity_name = row[1]
        activity_desc = row[2]
        rating = row[3]
        group_name = row[4]
        activity_image_url = row[5]
        activity_duration = row[6]

        print(f"Activity: {activity_name}, Rating: {rating} for group: {group_name}")
        activities.append(f"Activity: {activity_name}, Activity Description: {activity_desc}, Rating: {rating}, Activity Image URL: {activity_image_url}, Duration: {activity_duration}")

    cursor.close()
    conn.close()
    return activities


@track
def get_activities_by_group_type_or_travel_theme(
    group_type: str, 
    travel_theme: str, 
    destination: str
    ) -> List[str]:
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(os.getenv('VECTOR_DB_URL'))
        cursor = conn.cursor()

        if not destination:
            return {"error": "Destination is required"}

        # Get travel group ID (if provided)
        travel_group_id = None
        if group_type:
            cursor.execute("SELECT id FROM travel_group WHERE name ILIKE %s", (group_type,))
            result = cursor.fetchone()
            if result:
                travel_group_id = result[0]

        # Get travel theme ID (if provided)
        travel_theme_id = None
        if travel_theme:
            cursor.execute("SELECT id FROM travel_theme WHERE name ILIKE %s", (travel_theme,))
            result = cursor.fetchone()
            if result:
                travel_theme_id = result[0]

        # Get destination ID
        cursor.execute("SELECT id FROM destination WHERE name ILIKE %s", (destination,))
        destination_id = cursor.fetchone()

        if not destination_id:
            # call LLM to create activities based on destination
            destination = destination.lower()
            system_prompt = """You are world class trip itinerary builder, 
            Your task is to suggest activities for the group_type, travel_theme and destination provided to you.
            Give maximum 5 activities only.
            Create concise but efficient activities suggestion for a user and give user a would class experience.
            """
            client = AzureOpenAI(
                api_key=os.getenv('OPENAI_API_KEY'),
                azure_endpoint=os.getenv('AZURE_DEPLOYMENT'),
                azure_deployment='gpt-4o-mvp-dev',
                api_version='2024-02-15-preview'
            )

            response = client.chat.completions.create(
                model='gpt-4o',
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": f"""create activities for a user based on this information,
                        "destination": {destination},
                        "group_type": {str(group_type)},
                        "travel_theme": {str(travel_theme)}
                        """
                    }
                ],
                temperature=0.6,
            )
            message = response.choices[0].message.content
            return {"activities": message}

        destination_id = destination_id[0]

        # Get must-travel activities specific to the destination
        must_travel_query = """
            SELECT 
                mta.name AS activity_name, 
                mta.description,
                mtgt.rating, 
                'must' AS activity_type,
                mta.activity_image_url,
                mta.activity_duration
            FROM must_travel_activity mta
            JOIN must_activity_group_theme mtgt ON mta.id = mtgt.must_travel_activity_id
            WHERE mta.destination_id = %s
        """
        must_travel_params = [destination_id]
        if travel_group_id:
            must_travel_query += " AND mtgt.travel_group_id = %s"
            must_travel_params.append(travel_group_id)
        if travel_theme_id:
            must_travel_query += " AND mtgt.travel_theme_id = %s"
            must_travel_params.append(travel_theme_id)

        # Add ORDER BY and LIMIT clauses for top 2
        must_travel_query += " ORDER BY mtgt.rating DESC LIMIT 2"

        cursor.execute(must_travel_query, tuple(must_travel_params))
        must_travel_activities = cursor.fetchall()

        # Get recommended activities specific to the destination
        recommended_query = """
            SELECT 
                rta.name AS activity_name, 
                rta.description,
                rtgt.rating,
                'recommended' AS activity_type,
                rta.activity_image_url,
                rta.activity_duration
            FROM recommended_activity rta
            JOIN recommend_activity_group_theme rtgt ON rta.id = rtgt.recommend_activity_id
            WHERE rta.destination_id = %s
        """
        recommended_params = [destination_id]
        if travel_group_id:
            recommended_query += " AND rtgt.travel_group_id = %s"
            recommended_params.append(travel_group_id)
        if travel_theme_id:
            recommended_query += " AND rtgt.travel_theme_id = %s"
            recommended_params.append(travel_theme_id)

        # Add ORDER BY and LIMIT clauses for top 2
        recommended_query += " ORDER BY rtgt.rating DESC LIMIT 2"

        cursor.execute(recommended_query, tuple(recommended_params))
        recommended_activities = cursor.fetchall()

        activity_list = [
            {"activity_name": act[0], "description": act[1], "rating": act[2], "activity_type": act[3], "activity_image_url": act[4], "activity_duration": act[5]}
            for act in must_travel_activities + recommended_activities
        ]

        # Close the connection
        cursor.close()
        conn.close()

        # Return structured JSON response
        return {
            "activities": activity_list
        }

    except Exception as e:
        return {"error": str(e)}


def get_confirm_button() -> str:
    return 'confirm button'
