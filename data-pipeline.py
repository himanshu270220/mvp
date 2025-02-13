from sqlalchemy import create_engine, Column, String
from sqlalchemy.orm import Session
from database_schema import Destination, Hotel, HotelMaster, Location, LocationGroupTheme, MustActivityGroupTheme, MustTravelActivity, MustTravelActivityMaster, Pair, RecommendActivityGroupTheme, RecommendedActivity, RecommendedActivityMaster, Region, TravelGroup, TravelGroupMaster, TravelTheme, TravelThemeMaster
from openai import OpenAI
import numpy as np
from typing import List, Dict, Any
import os
from datetime import datetime
import logging
from dotenv import load_dotenv
from database_schema import Base

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseSync:
    def __init__(self):
        self.master_engine = create_engine(os.getenv('MASTER_DB_URL'))
        self.chatbot_engine = create_engine(os.getenv('VECTOR_DB_URL'))
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
    def get_embedding(self, text: str) -> List[float]:
        response = self.client.embeddings.create(
            input=[f"{text}"],
            model="text-embedding-ada-002"
        )

        embedding_vector = response.data[0].embedding
        return embedding_vector

    def initialize_chatbot_db(self):
        """Initialize all tables in chatbot database if they don't exist"""
        try:
            Base.metadata.create_all(self.chatbot_engine)
            print("Successfully initialized chatbot database tables")
        except Exception as e:
            print(f"Error initializing chatbot database: {str(e)}")
            raise
    
    def sync_regions(self):
        with Session(self.master_engine) as master_session, Session(self.chatbot_engine) as chatbot_session:
            regions = master_session.query(Region).all()
            
            for region in regions:
                # Using the region name for embedding since it's the main identifier
                # embedding = self.get_embedding(region.region)
                
                chatbot_region = chatbot_session.query(Region).filter_by(id=region.id).first()
                if not chatbot_region:
                    chatbot_region = Region(
                        id=region.id,
                        region=region.region,
                        # embedding=embedding
                    )
                    chatbot_session.add(chatbot_region)
                else:
                    # chatbot_region.embedding = embedding
                    pass
            
            chatbot_session.commit()
    
    def sync_pairs(self):
        with Session(self.master_engine) as master_session, Session(self.chatbot_engine) as chatbot_session:
            pairs = master_session.query(Pair).all()
            
            for pair in pairs:
                # Using the destination_pair field for embedding
                # embedding = self.get_embedding(pair.destination_pair)
                
                chatbot_pair = chatbot_session.query(Pair).filter_by(id=pair.id).first()
                if not chatbot_pair:
                    chatbot_pair = Pair(
                        id=pair.id,
                        destination_pair=pair.destination_pair,
                        # embedding=embedding
                    )
                    chatbot_session.add(chatbot_pair)
                else:
                    pass
            
            chatbot_session.commit()

    def sync_destinations(self):
        with Session(self.master_engine) as master_session, Session(self.chatbot_engine) as chatbot_session:
            destinations = master_session.query(Destination).all()
            
            for dest in destinations:
                combined_text = f"{dest.name} {dest.description}"
                # embedding = self.get_embedding(combined_text)
                
                chatbot_dest = chatbot_session.query(Destination).filter_by(id=dest.id).first()
                if not chatbot_dest:
                    chatbot_dest = Destination(
                        id=dest.id,
                        name=dest.name,
                        code=dest.code,
                        description=dest.description,
                        region_id=dest.region_id,
                        pair_id=dest.pair_id,
                        # embedding=embedding
                    )
                    chatbot_session.add(chatbot_dest)
                else:
                    # chatbot_dest.embedding = embedding
                    pass
            
            chatbot_session.commit()

    def sync_locations(self):
        with Session(self.master_engine) as master_session, Session(self.chatbot_engine) as chatbot_session:
            locations = master_session.query(Location).all()
            
            for loc in locations:
                combined_text = f"{loc.name} {loc.description}"
                # embedding = self.get_embedding(combined_text)
                
                chatbot_loc = chatbot_session.query(Location).filter_by(id=loc.id).first()
                if not chatbot_loc:
                    chatbot_loc = Location(
                        id=loc.id,
                        name=loc.name,
                        description=loc.description,
                        destination_id=loc.destination_id,
                        # embedding=embedding
                    )
                    chatbot_session.add(chatbot_loc)
                else:
                    # chatbot_loc.embedding = embedding
                    pass
            
            chatbot_session.commit()

    def sync_travel_groups(self):
        with Session(self.master_engine) as master_session, Session(self.chatbot_engine) as chatbot_session:
            travel_groups = master_session.query(TravelGroupMaster).all()
            
            for group in travel_groups:
                combined_text = f"{group.name}, {group.description}"
                embedding = self.get_embedding(combined_text)
                
                chatbot_group = chatbot_session.query(TravelGroup).filter_by(id=group.id).first()
                if not chatbot_group:
                    chatbot_group = TravelGroup(
                        id=group.id,
                        name=group.name,
                        code=group.code,
                        description=group.description,
                        embedding=embedding
                    )
                    chatbot_session.add(chatbot_group)
                else:
                    chatbot_group.embedding = embedding
            
            chatbot_session.commit()

    def sync_travel_themes(self):
        with Session(self.master_engine) as master_session, Session(self.chatbot_engine) as chatbot_session:
            themes = master_session.query(TravelThemeMaster).all()
            
            for theme in themes:
                # Combine name and description for richer embedding
                combined_text = f"{theme.name}, {theme.description}"
                embedding = self.get_embedding(combined_text)
                
                chatbot_theme = chatbot_session.query(TravelTheme).filter_by(id=theme.id).first()
                if not chatbot_theme:
                    chatbot_theme = TravelTheme(
                        id=theme.id,
                        name=theme.name,
                        code=theme.code,
                        description=theme.description,
                        embedding=embedding
                    )
                    chatbot_session.add(chatbot_theme)
                else:
                    chatbot_theme.embedding = embedding
            
            chatbot_session.commit()

    def sync_location_group_themes(self):
        with Session(self.master_engine) as master_session, Session(self.chatbot_engine) as chatbot_session:
            location_group_themes = master_session.query(LocationGroupTheme).all()
            
            for lgt in location_group_themes:
                chatbot_lgt = chatbot_session.query(LocationGroupTheme).filter_by(
                    location_id=lgt.location_id,
                    travel_group_id=lgt.travel_group_id,
                    travel_theme_id=lgt.travel_theme_id
                ).first()
                
                if not chatbot_lgt:
                    chatbot_lgt = LocationGroupTheme(
                        id=lgt.id,
                        location_id=lgt.location_id,
                        travel_group_id=lgt.travel_group_id,
                        travel_theme_id=lgt.travel_theme_id,
                        rating=lgt.rating
                    )
                    chatbot_session.add(chatbot_lgt)
                else:
                    chatbot_lgt.rating = lgt.rating
            
            chatbot_session.commit()
            
    def sync_activities(self):
        with Session(self.master_engine) as master_session, Session(self.chatbot_engine) as chatbot_session:
            for Activity in [MustTravelActivityMaster, RecommendedActivityMaster]:
                activities = (
                    master_session.query(
                        Activity,
                        Destination.name.label('destination_name')
                    )
                    .join(Destination, Activity.destination_id == Destination.id)
                    .all()
                )
                
                for act, destination_name in activities:
                    combined_text = f"{act.name}, {act.description} in {destination_name}"
                    embedding = self.get_embedding(combined_text)
                    
                    ActivityNew = MustTravelActivity if Activity == MustTravelActivityMaster else RecommendedActivity
                    chatbot_act = chatbot_session.query(ActivityNew).filter_by(id=act.id).first()
                    if not chatbot_act:
                        chatbot_act = ActivityNew(
                            id=act.id,
                            name=act.name,
                            code=act.code,
                            description=act.description,
                            destination_id=act.destination_id,
                            embedding=embedding,
                            activity_image_url=act.activity_image_url,
                            activity_duration=act.activity_duration
                        )
                        chatbot_session.add(chatbot_act)
                    else:
                        chatbot_act.embedding = embedding
                
                chatbot_session.commit()
   
    def sync_must_activity_group_themes(self):
        with Session(self.master_engine) as master_session, Session(self.chatbot_engine) as chatbot_session:
            must_activity_group_themes = master_session.query(MustActivityGroupTheme).all()
            
            for magt in must_activity_group_themes:
                chatbot_magt = chatbot_session.query(MustActivityGroupTheme).filter_by(
                    must_travel_activity_id=magt.must_travel_activity_id,
                    travel_group_id=magt.travel_group_id,
                    travel_theme_id=magt.travel_theme_id
                ).first()
                
                if not chatbot_magt:
                    chatbot_magt = MustActivityGroupTheme(
                        id=magt.id,
                        must_travel_activity_id=magt.must_travel_activity_id,
                        travel_group_id=magt.travel_group_id,
                        travel_theme_id=magt.travel_theme_id,
                        rating=magt.rating,
                    )
                    chatbot_session.add(chatbot_magt)
                else:
                    chatbot_magt.rating = magt.rating
            
            chatbot_session.commit()

    def sync_recommend_activity_group_themes(self):
        with Session(self.master_engine) as master_session, Session(self.chatbot_engine) as chatbot_session:
            recommend_activity_group_themes = master_session.query(RecommendActivityGroupTheme).all()
            
            for ragt in recommend_activity_group_themes:
                chatbot_ragt = chatbot_session.query(RecommendActivityGroupTheme).filter_by(
                    recommend_activity_id=ragt.recommend_activity_id,
                    travel_group_id=ragt.travel_group_id,
                    travel_theme_id=ragt.travel_theme_id
                ).first()
                
                if not chatbot_ragt:
                    chatbot_ragt = RecommendActivityGroupTheme(
                        id=ragt.id,
                        recommend_activity_id=ragt.recommend_activity_id,
                        travel_group_id=ragt.travel_group_id,
                        travel_theme_id=ragt.travel_theme_id,
                        rating=ragt.rating
                    )
                    chatbot_session.add(chatbot_ragt)
                else:
                    chatbot_ragt.rating = ragt.rating
            
            chatbot_session.commit()

    def sync_hotels(self):
        with Session(self.master_engine) as master_session, Session(self.chatbot_engine) as chatbot_session:
            hotels = (
                master_session.query(
                    HotelMaster,
                    Location.name.label('location_name'),
                    Destination.name.label('destination_name')
                )
                .join(Location, Hotel.location_id == Location.id)
                .join(Destination, Location.destination_id == Destination.id)
                .all()
            )
            
            for hotel, location_name, destination_name in hotels:
                combined_text = f"{hotel.name}, {hotel.description} in {location_name}, {destination_name}. {hotel.star} star hotel with rating {hotel.rating}"
                embedding = self.get_embedding(combined_text)
                
                chatbot_hotel = chatbot_session.query(Hotel).filter_by(id=hotel.id).first()
                if not chatbot_hotel:
                    chatbot_hotel = Hotel(
                        id=hotel.id,
                        name=hotel.name,
                        description=hotel.description,
                        location=hotel.location,
                        location_id=hotel.location_id,
                        star=hotel.star,
                        rating=hotel.rating,
                        embedding=embedding
                    )
                    chatbot_session.add(chatbot_hotel)
                else:
                    chatbot_hotel.embedding = embedding
            
            chatbot_session.commit()


def run_sync():
    try:
        logger.info(f"Starting database sync at {datetime.now()}")
        sync = DatabaseSync()

        sync.initialize_chatbot_db()
        
        sync.sync_regions()
        logger.info("Regions synced successfully")

        sync.sync_pairs()
        logger.info("Pairs synced successfully")
        
        sync.sync_destinations()
        logger.info("Destinations synced successfully")
        
        sync.sync_locations()
        logger.info("Locations synced successfully")

        sync.sync_travel_groups()  
        logger.info("Travel groups synced successfully")

        sync.sync_travel_themes()
        logger.info("Travel themes synced successfully")

        sync.sync_location_group_themes()
        logger.info("Location group themes synced successfully")
        
        sync.sync_activities()
        logger.info("Activities synced successfully")

        

        sync.sync_must_activity_group_themes()
        logger.info("Must activity group themes synced successfully")

        sync.sync_recommend_activity_group_themes()
        logger.info("Recommend activity group themes synced successfully")
        
        sync.sync_hotels()
        logger.info("Hotels synced successfully")

        logger.info(f"Database sync completed at {datetime.now()}")
        
    except Exception as e:
        logger.error(f"Error during sync: {str(e)}")
        raise

if __name__ == "__main__":
    run_sync()