from typing import List
from dotenv import load_dotenv
import psycopg2
import openai
import os
from opik.integrations.openai import track_openai
from opik import track

from azent.SimpleAgent import SimpleAgent

load_dotenv()


@track
def get_hotels_by_destination(
        destination: str,
        group_type: str,
        travel_theme: str,
        star_rating: int = 5,
        hotel_description: str = None
) -> List[str]:
    """
    Get hotels by either location or destination name, with optional hotel description for semantic search.
    
    Args:
        destination: Location or destination name
        hotel_description: Optional description to find semantically similar hotels
    """
    conn = psycopg2.connect(os.getenv("VECTOR_DB_URL"))
    cursor = conn.cursor()

    print("Searching hotels for:", destination)

    if hotel_description:
        # Create embedding for hotel description
        response = openai.embeddings.create(
            input=[hotel_description],
            model="text-embedding-ada-002"
        )
        query_embedding = response.data[0].embedding
        query_vector_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        sql = f"""
            SELECT 
                h.id,
                h.name,
                l.name as location_name,
                d.name as destination_name,
                -(h.embedding <#> %s::vector) as similarity
            FROM hotel h
            JOIN location l ON h.location_id = l.id
            JOIN destination d ON l.destination_id = d.id
            WHERE 
                (h.star = {star_rating})
                AND (l.name ILIKE %s OR d.name ILIKE %s)
                AND -(h.embedding <#> %s::vector) > 0.85
            ORDER BY similarity DESC
            LIMIT 5;
        """
        cursor.execute(sql, (
            query_vector_str,
            f"%{destination}%",
            f"%{destination}%",
            query_vector_str
        ))
    else:
        # Simple location/destination based search
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
            try:
                destination = destination.lower()
                trip_agent = SimpleAgent(
                    base_url=os.getenv("LLM_API_URL"),
                    api_key=os.getenv("LLM_API_KEY"),
                    system_prompt="""You are world class trip itinerary builder, 
                                        Your task is to suggest hotels for the group_type, travel_theme and destination provided to you.

                                        suggest concise but efficient hotels suggestion for a user and give user a would class experience.
                                        return the response in given JSON format:
                                        {{
                                            "hotels": [
                                                {{
                                                    "title": <title>,
                                                    "description": <description>,
                                                    "rating": <rating>,
                                                    "hotel_rating": <hotel_rating>,
                                                    "location": <location>  
                                                }}
                                            ]
                                        }}
                                        """,
                    output_format={"type": "json_object"}
                )

                response = trip_agent.execute(
                   f"""suggest hotels for a user based on this information,
                    destination: {destination},
                    group_type: {str(group_type)},
                    travel_theme: {str(travel_theme)}
                    """
               )

                return response['hotels']
            except Exception as e:
                return []

        destination_id = destination_id[0]

        query = f"""
                    SELECT 
                        h.name AS hotel_name,
                        h.description AS hotel_description,
                        h.star AS hotel_star,
                        h.rating AS hotel_rating,
                        l.name AS location_name,
                        lgt.rating AS location_rating,
                        d.name AS destination_name,
                        tg.name AS group_name,
                        tt.name AS theme_name
                    FROM hotel h
                    JOIN location l ON h.location_id = l.id
                    JOIN location_group_theme lgt ON l.id = lgt.location_id
                    JOIN destination d ON l.destination_id = d.id
                    LEFT JOIN travel_group tg ON lgt.travel_group_id = tg.id
                    LEFT JOIN travel_theme tt ON lgt.travel_theme_id = tt.id
                    WHERE l.destination_id = %s AND h.star = {star_rating}
                """

        query_params = [destination_id]

        # Add filters if provided
        if travel_group_id:
            query += " AND lgt.travel_group_id = %s"
            query_params.append(travel_group_id)
        if travel_theme_id:
            query += " AND lgt.travel_theme_id = %s"
            query_params.append(travel_theme_id)

        # Add ordering by hotel rating and limit
        query += """ 
            ORDER BY 
            lgt.rating DESC,
            h.rating DESC
            LIMIT 5
        """

        # Execute the query
        cursor.execute(query, tuple(query_params))
        hotels = cursor.fetchall()

        # Format the results
        hotel_list = [
            {
                "title": hotel[0],
                "description": hotel[1],
                "rating": hotel[2] if hotel[2] else 0,
                "hotel_rating": hotel[3] if hotel[3] else 0,
                "location": hotel[4],  
            }
            for hotel in hotels
        ]

        # Close the connection
        cursor.close()
        conn.close()

        return hotel_list
