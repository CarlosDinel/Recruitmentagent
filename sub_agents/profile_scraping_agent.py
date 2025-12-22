"""This agent is a sub-agent of the sourcing_manager.py agent. It is resposible for getting more detailed profiles out of the candidates that 
have been ingested by the candidate_searching_agent.py. The agent utilizes various tools and APIs to scrape detailed profile information from LinkedIn, ensuring that comprehensive data is available for further evaluation and decision-making in the recruitment process.
This agent also updates existing candidate profiles with newly scraped information to maintain data accuracy and relevance. This updates will be stored by the database_agent.py.

"""


#  ---- Package imports ----
from typing import  List, Annotated, Sequence, Dict, Any , Optional
from langgraph.graph import START, END, StateGraph
from typing_extensions import TypedDict
from dotenv import load_dotenv
import os
import numpy as np
