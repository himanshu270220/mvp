from Azent.SimpleAgent import SimpleAgent
from typing import List
from dotenv import load_dotenv
import psycopg2
from openai import AzureOpenAI
import os
from opik.integrations.openai import track_openai
from opik import track
from logger import logger


load_dotenv()


@track
def get_activities_by_activity_name(acitivity: str, location: str) -> List[str]:
    logger.info(f"Getting activities for activity: {acitivity} in location: {location}")
    try:
        conn = psycopg2.connect(os.getenv("VECTOR_DB_URL"))
        logger.debug("Database connection established")
        cursor = conn.cursor()

        logger.debug(f"Processing location: {location}")
        openai_client = AzureOpenAI(
            api_key=os.getenv('OPENAI_API_KEY'),
            azure_deployment=os.getenv('AZURE_DEPLOYMENT'),
            azure_endpoint='gpt-4o-mvp-dev',
            azure_api_version='2024-02-15-preview'
        )

        logger.debug("Generating embeddings for activity and location")
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

        logger.debug(f"Retrieved location_id: {location_id}")

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
            activity_id = row[0]
            activity_name = row[1]
            activity_desc = row[2]
            distance = row[3]
            logger.debug(f"Found activity: {activity_name}, Distance: {distance}")
            activities.append(activity_name)

        cursor.close()
        conn.close()
        logger.info(f"Successfully retrieved {len(activities)} activities")
        return activities
    except Exception as e:
        logger.error(f"Error in get_activities_by_activity_name: {str(e)}", exc_info=True)
        raise


@track
def get_activities_by_group_type(group_type: str, location: str) -> List[str]:
    logger.info(f"Getting activities for group type: {group_type} in location: {location}")
    try:
        conn = psycopg2.connect(os.getenv("VECTOR_DB_URL"))
        logger.debug("Database connection established")
        cursor = conn.cursor()

        logger.debug(f"Processing group type: {group_type}")
        # openai_client = AzureOpenAI(
        #     api_key=os.getenv('OPENAI_API_KEY'),
        #     azure_deployment=os.getenv('AZURE_DEPLOYMENT'),
        #     azure_endpoint='gpt-4o-mvp-dev',
        #     azure_api_version='2024-02-15-preview'
        # )
        #
        # response = openai_client.embeddings.create(
        #     input=[f"group_type: {group_type}"],
        #     model="text-embedding-ada-002"
        # )
        #
        # query_embedding = response.data[0].embedding
        query_vector_str = "[" + ",".join(str(x) for x in []) + "]"

        # get location id
        cursor.execute(f"SELECT id FROM destination WHERE name ILIKE '{location}'")
        row = cursor.fetchone()
        location_id = row[0]

        logger.debug(f"Retrieved location_id: {location_id}")

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

            logger.debug(f"Found activity: {activity_name}, Rating: {rating} for group: {group_name}")
            activities.append(f"Activity: {activity_name}, Activity Description: {activity_desc}, Rating: {rating}, Activity Image URL: {activity_image_url}, Duration: {activity_duration}")

        cursor.close()
        conn.close()
        logger.info(f"Successfully retrieved {len(activities)} activities")
        return activities
    except Exception as e:
        logger.error(f"Error in get_activities_by_group_type: {str(e)}", exc_info=True)
        raise


@track
def get_activities_by_group_type_or_travel_theme_and_number_of_days(
    group_type: str, 
    travel_theme: str, 
    destination: str,
    number_of_days: float
    ) -> List[str]:
    logger.info(f"Getting activities for group type: {group_type}, travel theme: {travel_theme}, destination: {destination}, days: {number_of_days}")
    try:
        conn = psycopg2.connect(os.getenv('VECTOR_DB_URL'))
        logger.debug("Database connection established")
        cursor = conn.cursor()

        if not destination:
            logger.warning("Destination is required but not provided")
            return {"error": "Destination is required"}
        
        if number_of_days <= 0:
            logger.warning("Number of days must be greater than 0")
            return {"error": "Number of days must be greater than 0"}

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
            logger.info("Destination not found in database, falling back to LLM")
            try:
                destination = destination.lower()
                trip_agent = SimpleAgent(
                    base_url=os.getenv("LLM_API_URL"),
                    api_key=os.getenv("LLM_API_KEY"),
                    system_prompt="""You are world class trip itinerary builder, 
                            Your task is to suggest activities for the group_type, travel_theme and destination provided to you.
                            Each activity should have an estimated duration (0.5 for half day, 1 for full day).
                            Total duration of all activities should not exceed the number_of_days provided.
                            Create concise but efficient activities suggestion for a user and give user a world class experience.
                            Return output in given JSON format:
                            {{
                                "activities": [
                                    {{
                                         "title": <title>,
                                        "description": <description>,
                                        "rating": <rating>,
                                        "activity_type": <activity_type>,
                                        "image": <image>,
                                        "duration":<duration>
                                    }}
                                ]
                            }}
                            """,
                    output_format={"type": "json_object"}
                )

                trip_response = trip_agent.execute(
                    f"""create activities for a user based on this information,
                    "destination": {destination},
                    "group_type": "couple",
                    "travel_theme": "culture",
                    "number_of_days": 3"""
                )
                logger.info("Successfully generated activities using LLM")
                return trip_response['activities']
            except Exception as e:
                logger.error(f"Error generating activities with LLM: {str(e)}", exc_info=True)
                return []

        destination_id = destination_id[0]

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

        must_travel_query += " ORDER BY mtgt.rating DESC"

        cursor.execute(must_travel_query, tuple(must_travel_params))
        must_travel_activities = cursor.fetchall()

        # Get all recommended activities (without LIMIT)
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

        recommended_query += " ORDER BY rtgt.rating DESC"

        cursor.execute(recommended_query, tuple(recommended_params))
        recommended_activities = cursor.fetchall()

        # Convert all activities to list of dicts for easier processing
        all_activities = [
            {
                "title": act[0],
                "description": act[1],
                "rating": act[2],
                "activity_type": act[3],
                "image": act[4],
                "duration": float(act[5])
            }
            for act in must_travel_activities + recommended_activities
        ]

        # Sort activities by rating and type (must-travel first)
        sorted_activities = sorted(
            all_activities,
            key=lambda x: (x["activity_type"] != "must", -x["rating"])
        )

        # Select activities that fit within the number of days
        selected_activities = []
        total_duration = 0.0

        for activity in sorted_activities:
            if total_duration + activity["duration"] <= number_of_days:
                selected_activities.append(activity)
                total_duration += activity["duration"]
            
            # Break if we've filled the days or reached 5 activities
            if total_duration >= number_of_days or len(selected_activities) >= 5:
                break

        cursor.close()
        conn.close()

        logger.info(f"Successfully retrieved {len(selected_activities)} activities within {number_of_days} days")
        return selected_activities

    except Exception as e:
        logger.error(f"Error in get_activities_by_group_type_or_travel_theme_and_number_of_days: {str(e)}", exc_info=True)
        return {"error": str(e)}


def get_confirm_button() -> str:
    return 'confirm button'
