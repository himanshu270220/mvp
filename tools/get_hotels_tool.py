from typing import List
from dotenv import load_dotenv
import psycopg2
import openai
import os

from openai import OpenAI
from opik.integrations.openai import track_openai
from opik import track

from Azent.SimpleAgent import SimpleAgent
from logger import logger

load_dotenv()
openai_client = OpenAI(
    api_key=os.getenv("LLM_API_KEY"),
    base_url=os.getenv("LLM_BASE_URL")
)

@track
def get_hotels_by_destination(
        destination: str = None,
        group_type: str = None,
        travel_theme: str = None,
        star_rating: int = 5,
        hotel_description: str = None
) -> List[str]:
    """
    Get hotels by either destination name, group_type, travel_theme, star_rating, hotel_description
    
    Args:
        destination: Location or destination name
        hotel_description: Hotel description
        travel_theme: Travel theme
        star_rating: Star rating
        group_type: Group type
    """
    try:
        conn = psycopg2.connect(os.getenv("VECTOR_DB_URL"))
        cursor = conn.cursor()

        print("Searching hotels for:", destination)

        if hotel_description:
            response = openai_client.embeddings.create(
                input=[hotel_description],
                model="text-embedding-ada-002"
            )
            query_embedding = response.data[0].embedding
            query_vector_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

            sql = """
                SELECT 
                    h.id,
                    h.name,
                    l.name as location_name,
                    d.name as destination_name,
                    -(h.embedding <#> %s) as similarity
                FROM hotel h
                JOIN location l ON h.location_id = l.id
                JOIN destination d ON l.destination_id = d.id
                WHERE 
                    h.star = %s
                    AND (l.name ILIKE %s OR d.name ILIKE %s)
                    AND -(h.embedding <#> %s) > 0.30
                ORDER BY similarity DESC
                LIMIT 5;
            """

            # Create tuple of parameters in the correct order
            params = (
                query_vector_str,  # For first vector comparison
                star_rating,
                f"%{destination}%",
                f"%{destination}%",
                query_vector_str  # For second vector comparison
            )

            cursor.execute(sql, params)  # Pass params directly, not as a tuple of a list

            hotels = cursor.fetchall()

            hotel_list = [
                f'{row[1]} at {row[2]}, {row[3]}'
                for row in hotels
            ]

            # Close the connection
            cursor.close()
            conn.close()
            return hotel_list

        else:
            travel_group_id = None
            if group_type:
                cursor.execute("SELECT id FROM travel_group WHERE name ILIKE %s", (group_type,))
                result = cursor.fetchone()
                if result:
                    travel_group_id = result[0]

            travel_theme_id = None
            if travel_theme:
                cursor.execute("SELECT id FROM travel_theme WHERE name ILIKE %s", (travel_theme,))
                result = cursor.fetchone()
                if result:
                    travel_theme_id = result[0]

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
                            WHERE l.destination_id = %s
                        """

            query_params = [destination_id]

            if travel_group_id:
                query += " AND lgt.travel_group_id = %s"
                query_params.append(travel_group_id)
            if travel_theme_id:
                query += " AND lgt.travel_theme_id = %s"
                query_params.append(travel_theme_id)

            if star_rating:
                query += " AND h.star = %s"
                query_params.append(star_rating)

            query += """ 
                    ORDER BY 
                    lgt.rating DESC,
                    h.rating DESC
                    LIMIT 5
                """

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

            return [hotel_list[0]] if hotel_list else []
    except Exception as e:
        print(e)
        logger.error(e)


@track
def get_hotels(
        destination: str,
        group_type: str = None,
        travel_theme: str = None,
        star_rating: int = 5,
        hotel_description: str = None
) -> List[str]:
    """
    Get hotels by either destination name, group_type, travel_theme, star_rating, hotel_description

    Args:
        destination: Location or destination name
        hotel_description: Hotel description
        travel_theme: Travel theme
        star_rating: Star rating
        group_type: Group type
    """
    try:
        conn = psycopg2.connect(os.getenv("VECTOR_DB_URL"))
        cursor = conn.cursor()

        print("Searching hotels for:", destination)

        if hotel_description:
            response = openai_client.embeddings.create(
                input=[hotel_description],
                model="text-embedding-ada-002"
            )
            query_embedding = response.data[0].embedding
            query_vector_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

            sql = """
                SELECT 
                    h.id,
                    h.name,
                    l.name as location_name,
                    d.name as destination_name,
                    -(h.embedding <#> %s) as similarity
                FROM hotel h
                JOIN location l ON h.location_id = l.id
                JOIN destination d ON l.destination_id = d.id
                WHERE 
                    h.star = %s
                    AND (l.name ILIKE %s OR d.name ILIKE %s)
                    AND -(h.embedding <#> %s) > 0.30
                ORDER BY similarity DESC
                LIMIT 5;
            """

            # Create tuple of parameters in the correct order
            params = (
                query_vector_str,  # For first vector comparison
                star_rating,
                f"%{destination}%",
                f"%{destination}%",
                query_vector_str  # For second vector comparison
            )

            cursor.execute(sql, params)  # Pass params directly, not as a tuple of a list

            hotels = cursor.fetchall()

            hotel_list = [
                f'{row[1]} at {row[2]}, {row[3]}'
                for row in hotels
            ]

            # Close the connection
            cursor.close()
            conn.close()
            return hotel_list

        else:
            travel_group_id = None
            if group_type:
                cursor.execute("SELECT id FROM travel_group WHERE name ILIKE %s", (group_type,))
                result = cursor.fetchone()
                if result:
                    travel_group_id = result[0]

            travel_theme_id = None
            if travel_theme:
                cursor.execute("SELECT id FROM travel_theme WHERE name ILIKE %s", (travel_theme,))
                result = cursor.fetchone()
                if result:
                    travel_theme_id = result[0]

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
            SELECT DISTINCT ON (h.id)
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
            WHERE l.destination_id = %s
            """

            query_params = [destination_id]

            if travel_group_id:
                query += " AND lgt.travel_group_id = %s"
                query_params.append(travel_group_id)
            if travel_theme_id:
                query += " AND lgt.travel_theme_id = %s"
                query_params.append(travel_theme_id)

            if star_rating:
                query += " AND h.star = %s"
                query_params.append(star_rating)

            query += """ 
                    ORDER BY 
                        h.id,                -- Must come first with DISTINCT ON
                        lgt.rating DESC,
                        h.rating DESC
                    LIMIT 5
                    """

            cursor.execute(query, tuple(query_params))
            hotels = cursor.fetchall()

            # Format the results
            hotel_list = [
                f'{hotel[0]}, rating {hotel[2]}' for hotel in hotels
            ]

            # Close the connection
            cursor.close()
            conn.close()

            return hotel_list if hotel_list else []
    except Exception as e:
        print(e)
        logger.error(e)