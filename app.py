import os
import io
import json
import pickle
from groq import Groq
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date, timedelta
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, DateRange, Dimension, Metric,
    FilterExpression, Filter, OrderBy
)
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build

st.set_page_config(page_title="Customer Success Website Analytics Dashboard", layout="wide")

# ── GLOBAL BUTTON STYLES ──────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Base button reset & shared styles ── */
.stButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 13.5px !important;
    letter-spacing: 0.2px !important;
    transition: all 0.18s ease !important;
    cursor: pointer !important;
    outline: none !important;
    border: 1.5px solid transparent !important;
}

/* ── Standard (secondary) buttons ── */
.stButton > button:not([kind="primary"]) {
    background: #FFFFFF !important;
    color: #1F4E79 !important;
    border: 1.5px solid #B8CCE0 !important;
    box-shadow: 0 1px 3px rgba(31,78,121,0.10),
                0 1px 2px rgba(31,78,121,0.06) !important;
}
.stButton > button:not([kind="primary"]):hover {
    background: #EEF4FB !important;
    border-color: #4C8BF5 !important;
    box-shadow: 0 0 0 3px rgba(76,139,245,0.18),
                0 2px 6px rgba(31,78,121,0.14) !important;
    color: #1F4E79 !important;
}
.stButton > button:not([kind="primary"]):active {
    background: #D6E8F7 !important;
    box-shadow: 0 0 0 3px rgba(76,139,245,0.25) !important;
    transform: translateY(1px) !important;
}
.stButton > button:not([kind="primary"]):focus {
    border-color: #4C8BF5 !important;
    box-shadow: 0 0 0 3px rgba(76,139,245,0.22) !important;
}

/* ── Primary buttons (Load / Refresh, Apply) ── */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #1A73E8 0%, #1558B8 100%) !important;
    color: #FFFFFF !important;
    border: 1.5px solid #1558B8 !important;
    box-shadow: 0 2px 6px rgba(26,115,232,0.35),
                0 1px 2px rgba(26,115,232,0.20) !important;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #1E7FFF 0%, #1A63D4 100%) !important;
    box-shadow: 0 0 0 3px rgba(26,115,232,0.22),
                0 4px 12px rgba(26,115,232,0.40) !important;
    transform: translateY(-1px) !important;
}
.stButton > button[kind="primary"]:active {
    background: linear-gradient(135deg, #1558B8 0%, #1044A0 100%) !important;
    box-shadow: 0 0 0 3px rgba(26,115,232,0.28) !important;
    transform: translateY(1px) !important;
}
.stButton > button[kind="primary"]:focus {
    box-shadow: 0 0 0 3px rgba(26,115,232,0.30),
                0 2px 6px rgba(26,115,232,0.35) !important;
}

/* ── Sidebar-specific: calendar nav ◀ ▶ ── */
[data-testid="stSidebar"] .stButton > button:not([kind="primary"]) {
    background: #F5F8FF !important;
    border: 1.5px solid #C8D9EE !important;
    color: #1F4E79 !important;
    box-shadow: 0 1px 2px rgba(31,78,121,0.08) !important;
    border-radius: 6px !important;
}
[data-testid="stSidebar"] .stButton > button:not([kind="primary"]):hover {
    background: #E3EEFA !important;
    border-color: #4C8BF5 !important;
    box-shadow: 0 0 0 3px rgba(76,139,245,0.15),
                0 2px 5px rgba(31,78,121,0.12) !important;
}

/* ── Dropdown trigger button — date picker ── */
[data-testid="stSidebar"] .stButton > button:first-of-type {
    text-align: left !important;
    background: #FFFFFF !important;
    border: 1.5px solid #B8CCE0 !important;
    border-radius: 8px !important;
    box-shadow: 0 1px 4px rgba(31,78,121,0.10) !important;
    color: #1F4E79 !important;
    font-weight: 500 !important;
}
[data-testid="stSidebar"] .stButton > button:first-of-type:hover {
    border-color: #4C8BF5 !important;
    box-shadow: 0 0 0 3px rgba(76,139,245,0.15),
                0 2px 6px rgba(31,78,121,0.12) !important;
}

/* ── Download buttons ── */
.stDownloadButton > button {
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    background: #FFFFFF !important;
    color: #0F6E56 !important;
    border: 1.5px solid #9FE1CB !important;
    box-shadow: 0 1px 3px rgba(15,110,86,0.10),
                0 1px 2px rgba(15,110,86,0.06) !important;
    transition: all 0.18s ease !important;
}
.stDownloadButton > button:hover {
    background: #E1F5EE !important;
    border-color: #1D9E75 !important;
    box-shadow: 0 0 0 3px rgba(29,158,117,0.18),
                0 2px 6px rgba(15,110,86,0.14) !important;
    transform: translateY(-1px) !important;
}
.stDownloadButton > button:active {
    transform: translateY(1px) !important;
    box-shadow: 0 0 0 3px rgba(29,158,117,0.25) !important;
}

/* ── Toggle ── */
.stToggle label {
    font-weight: 500 !important;
    font-size: 13.5px !important;
}

/* ── Expander ── */
.streamlit-expanderHeader {
    border-radius: 8px !important;
    border: 1.5px solid #D0E4F4 !important;
    box-shadow: 0 1px 3px rgba(31,78,121,0.07) !important;
    font-weight: 600 !important;
    color: #1F4E79 !important;
}
</style>
""", unsafe_allow_html=True)


# ── PROPERTY REGISTRY ────────────────────────────────────────────────────────
# Name, GA4 ID, domain — GSC URL is auto-matched from your verified sites list
PORTFOLIO = [
    {"name": "The Serenite Collection", "ga4_id": "509737908", "domain": "theserenite.com",      "keywords": ["serenite","theserenite","the serenite","serenite collection","tallman hotel","tallman","narrow gauge inn","amador hotel","groveland hotel","blue wing saloon","shaver lake village hotel"]},
    {"name": "Shooting Star Lodge",     "ga4_id": "480184188", "domain": "shootingstarlodge.com","keywords": ["shooting star lodge","shooting star","shootingstarlodge"]},
    {"name": "Luffu Club",              "ga4_id": "513226281", "domain": "luffuclub.com",         "keywords": ["luffu","luffu club","luffuclub"]},
    {"name": "Yo1 Luxury Resorts",      "ga4_id": "342014736", "domain": "yo1.com",              "keywords": ["yo1","yo1 luxury","yo1 resorts","yo1.com"]},
    {"name": "Dolphin Group of Hotels", "ga4_id": "514756369", "domain": "hoteldolphin.in",      "keywords": ["dolphin","dolphin hotel","hotel dolphin","dolphin group","hoteldolphin"]},
    {"name": "Hotel PR Residency", "ga4_id": "386144469", "domain": "hotelprresidency.com", "keywords": ["hotel pr residency","hotelprresidency","residency"]},
    {"name": "Aloha On the Ganges", "ga4_id": "384719891", "domain": "alohaontheganges.com", "keywords": ["aloha","aloha on the ganges","alohaontheganges","ganges"]},
    {"name": "Umaid Palace", "ga4_id": "387999680", "domain": "umaidpalace.com", "keywords": ["umaid","umaid palace","umaidpalace"]},
    {"name": "Sandhya Residency", "ga4_id": "384851382", "domain": "sandhyaresidency.com", "keywords": ["residency","sandhya","sandhya residency","sandhyaresidency"]},
    {"name": "Wonderla Amusement Parks & Resort (DNU)", "ga4_id": "357767337", "domain": "wonderla.com", "keywords": ["amusement","parks","wonderla","wonderla amusement parks   resort  dnu"]},
    {"name": "Hotel Arama Suites", "ga4_id": "385033695", "domain": "aramasuites.com", "keywords": ["arama","aramasuites","hotel arama suites"]},
    {"name": "Le ROI Hotels & Resorts", "ga4_id": "386227278", "domain": "leroihotels.com", "keywords": ["le roi hotels   resorts","leroihotels","roi"]},
    {"name": "Central Hotels", "ga4_id": "390880656", "domain": "centralhotels.in", "keywords": ["central","central hotels","centralhotels"]},
    {"name": "Hotel Swagath, Bangalore", "ga4_id": "387055987", "domain": "hotelswagath.com", "keywords": ["hotel swagath  bangalore","hotelswagath","swagath"]},
    {"name": "Hotel Yasodha Towers", "ga4_id": "384824997", "domain": "hotelyasodhatowers.in", "keywords": ["hotel yasodha towers","hotelyasodhatowers","towers","yasodha"]},
    {"name": "GenX Hotels India - Redirect", "ga4_id": "384871130", "domain": "genxhotels.com", "keywords": ["genx","genx hotels india   redirect","genxhotels","india"]},
    {"name": "Ocean Palms Goa", "ga4_id": "388001502", "domain": "oceanpalmsgoa.com", "keywords": ["ocean","ocean palms goa","oceanpalmsgoa","palms"]},
    {"name": "Fantasy Golf Resort, Bangalore", "ga4_id": "367673121", "domain": "fantasygolfresort.com", "keywords": ["fantasy","fantasy golf resort  bangalore","fantasygolfresort","golf"]},
    {"name": "IRIS Hotel, Brigade Road, Bangalore", "ga4_id": "386137592", "domain": "irishotel.biz", "keywords": ["brigade","iris","iris hotel  brigade road  bangalore","irishotel","road"]},
    {"name": "Ganga Lahari, Haridwar", "ga4_id": "362500433", "domain": "gangalahari.com", "keywords": ["ganga","ganga lahari  haridwar","gangalahari","haridwar","lahari"]},
    {"name": "The Bungalows - Redirects", "ga4_id": "387390142", "domain": "thebungalows.co.in", "keywords": ["bungalows","the bungalows   redirects","thebungalows"]},
    {"name": "VITS - Hotels & Resorts", "ga4_id": "386667226", "domain": "vitshotels.com", "keywords": ["vits","vits   hotels   resorts","vitshotels"]},
    {"name": "Lotus Resorts and Hotels", "ga4_id": "387988978", "domain": "lotusresorthotels.com", "keywords": ["lotus","lotus resorts and hotels","lotusresorthotels"]},
    {"name": "Leisure Hotels", "ga4_id": "388045009", "domain": "leisurehotels.co.in", "keywords": ["leisure","leisure hotels","leisurehotels"]},
    {"name": "Our Native Village", "ga4_id": "400409149", "domain": "ournativevillage.com", "keywords": ["native","our","our native village","ournativevillage","village"]},
    {"name": "Springs Hotel & Spa, J.C. Road", "ga4_id": "385225792", "domain": "unknown", "keywords": ["road","spa","springs","springs hotel   spa  j c  road"]},
    {"name": "Aura Boutique Hotels", "ga4_id": "511820969", "domain": "auranewdelhi.com", "keywords": ["aura","aura boutique hotels","auranewdelhi","boutique"]},
    {"name": "Hotel Legend Inn", "ga4_id": "386697533", "domain": "thelegendinn.com", "keywords": ["hotel legend inn","legend","thelegendinn"]},
    {"name": "The Earl's Court DNU", "ga4_id": "387346321", "domain": "theearlscourtnainital.com", "keywords": ["court","earl","the earl s court dnu","theearlscourtnainital"]},
    {"name": "Abids Inn Homestay, Bangalore", "ga4_id": "383920325", "domain": "abidsinn.com", "keywords": ["abids","abids inn homestay  bangalore","abidsinn","homestay"]},
    {"name": "Hotel Ivory Tower, Bangalore", "ga4_id": "387581322", "domain": "ivorytowerhotel.com", "keywords": ["hotel ivory tower  bangalore","ivory","ivorytowerhotel","tower"]},
    {"name": "Tiger Camp Resort, Corbett", "ga4_id": "386759782", "domain": "habitathotels.com", "keywords": ["camp","corbett","habitathotels","tiger","tiger camp resort  corbett"]},
    {"name": "The Cosy Hotels", "ga4_id": "386407725", "domain": "thecosyhotels.com", "keywords": ["cosy","the cosy hotels","thecosyhotels"]},
    {"name": "Hotel Paraag, Rajbhavan Road, Bangalore", "ga4_id": "386972062", "domain": "hotelparaag.com", "keywords": ["hotel paraag  rajbhavan road  bangalore","hotelparaag","paraag","rajbhavan","road"]},
    {"name": "Maurya Hotel, Bangalore", "ga4_id": "386884433", "domain": "hotelmaurya.com", "keywords": ["hotelmaurya","maurya","maurya hotel  bangalore"]},
    {"name": "Golf Inn Executive Hotel, Bangalore", "ga4_id": "386906982", "domain": "golfinn.in", "keywords": ["executive","golf","golf inn executive hotel  bangalore","golfinn"]},
    {"name": "The Signature Inn Hotel, Bangalore", "ga4_id": "391702800", "domain": "thesignatureinn.in", "keywords": ["signature","the signature inn hotel  bangalore","thesignatureinn"]},
    {"name": "Udipi Home, Egmore, Chennai", "ga4_id": "386464719", "domain": "udipihome.in", "keywords": ["egmore","home","udipi","udipi home  egmore  chennai","udipihome"]},
    {"name": "Casa Cottage - Heritage Hotel in Bangalore", "ga4_id": "386137038", "domain": "casacottage.com", "keywords": ["casa","casa cottage   heritage hotel in bangalore","casacottage","cottage","heritage"]},
    {"name": "Welcome Group of Hotels, Delhi", "ga4_id": "524898348", "domain": "welcomegroupofhotel.com", "keywords": ["welcome","welcome group of hotels  delhi","welcomegroupofhotel"]},
    {"name": "The Carlton", "ga4_id": "289748349", "domain": "carlton-kodaikanal.com", "keywords": ["carlton","carlton-kodaikanal","the carlton"]},
    {"name": "Featherlite Evoma Hotel , Co-Working Space & Business Centre- K R Puram, Old Madras Road", "ga4_id": "387077520", "domain": "evomahotels.com", "keywords": ["evoma","evomahotels","featherlite","featherlite evoma hotel   co working space   business centre  k r puram  old madras road","space","working"]},
    {"name": "Holiday Home Resort, Kodaikanal", "ga4_id": "386201960", "domain": "holidayhomeresort.com", "keywords": ["holiday","holiday home resort  kodaikanal","holidayhomeresort","home","kodaikanal"]},
    {"name": "Hotel Siri Inn Hyderabad", "ga4_id": "386729855", "domain": "siriinn.com", "keywords": ["hotel siri inn hyderabad","siri","siriinn"]},
    {"name": "The Golden Crest Hotel Gangtok", "ga4_id": "386559613", "domain": "thegoldencrest.com", "keywords": ["crest","gangtok","golden","the golden crest hotel gangtok","thegoldencrest"]},
    {"name": "Daizzo Hotels", "ga4_id": "386877765", "domain": "themapleresidency.com", "keywords": ["daizzo","daizzo hotels","themapleresidency"]},
    {"name": "Pai Group of Hotels", "ga4_id": "386435848", "domain": "paihotels.com", "keywords": ["pai","pai group of hotels","paihotels"]},
    {"name": "Hotel SRM Grands –Chennai", "ga4_id": "386548236", "domain": "hotelsrmgrands.com", "keywords": ["grands","hotel srm grands  chennai","hotelsrmgrands","srm"]},
    {"name": "Online Suites, Bangalore - A unit of Shanthiniketan Homes", "ga4_id": "391731585", "domain": "onlinesuites.net", "keywords": ["homes","online","online suites  bangalore   a unit of shanthiniketan homes","onlinesuites","shanthiniketan"]},
    {"name": "Kadkani River Resort, Coorg", "ga4_id": "386195558", "domain": "kadkani.com", "keywords": ["coorg","kadkani","kadkani river resort  coorg","river"]},
    {"name": "Hotel White Conch Residency, Gangtok", "ga4_id": "368467837", "domain": "whiteconch.co.in", "keywords": ["conch","gangtok","hotel white conch residency  gangtok","residency","white","whiteconch"]},
    {"name": "THE RIALTO HOTEL", "ga4_id": "387218639", "domain": "rialtohotel.in", "keywords": ["rialto","rialtohotel","the rialto hotel"]},
    {"name": "Hotel Shivam, Pune", "ga4_id": "386357957", "domain": "shivamhotel.com", "keywords": ["hotel shivam  pune","shivam","shivamhotel"]},
    {"name": "Fort Abode Apartments, Fort Kochi", "ga4_id": "366349839", "domain": "fortabode.com", "keywords": ["abode","apartments","fort","fort abode apartments  fort kochi","fortabode"]},
    {"name": "Hotel Shivkrupa, Pune", "ga4_id": "386456639", "domain": "hotelshivkrupa.com", "keywords": ["hotel shivkrupa  pune","hotelshivkrupa","shivkrupa"]},
    {"name": "Maple Suites Serviced Apartments, Bangalore", "ga4_id": "386375928", "domain": "maplesuites.co.in", "keywords": ["apartments","maple","maple suites serviced apartments  bangalore","maplesuites","serviced"]},
    {"name": "Tranquil Resort, Wayanad", "ga4_id": "387404695", "domain": "tranquilresort.com", "keywords": ["tranquil","tranquil resort  wayanad","tranquilresort","wayanad"]},
    {"name": "Shetty Gardenia Hotel, Bangalore", "ga4_id": "386966450", "domain": "shettygardenia.com", "keywords": ["gardenia","shetty","shetty gardenia hotel  bangalore","shettygardenia"]},
    {"name": "Hometel Roorkee", "ga4_id": "387417718", "domain": "roorkeehometel.com", "keywords": ["hometel","hometel roorkee","roorkee","roorkeehometel"]},
    {"name": "Hotel Raviraj, Pune", "ga4_id": "387198111", "domain": "hotelraviraj.com", "keywords": ["hotel raviraj  pune","hotelraviraj","raviraj"]},
    {"name": "Hotel New Sreekrishna Residency, Hyderabad", "ga4_id": "386646741", "domain": "sreekrishnainn.com", "keywords": ["hotel new sreekrishna residency  hyderabad","new","residency","sreekrishna","sreekrishnainn"]},
    {"name": "Hotel Abhiraj Palace Jaipur", "ga4_id": "386956287", "domain": "hotelabhirajpalace.com", "keywords": ["abhiraj","hotel abhiraj palace jaipur","hotelabhirajpalace"]},
    {"name": "Indoasia Hotels", "ga4_id": "386866137", "domain": "indoasia-hotels.com", "keywords": ["indoasia","indoasia hotels","indoasia-hotels"]},
    {"name": "Hotel Abhineet Palace, Jaipur", "ga4_id": "387180078", "domain": "hotelabhineetpalace.com", "keywords": ["abhineet","hotel abhineet palace  jaipur","hotelabhineetpalace"]},
    {"name": "Lytton Hotel, Kolkata", "ga4_id": "368296747", "domain": "lyttonhotelindia.com", "keywords": ["lytton","lytton hotel  kolkata","lyttonhotelindia"]},
    {"name": "Hotel Maple Regency, Kochi", "ga4_id": "386220343", "domain": "hotelmapleregency.com", "keywords": ["hotel maple regency  kochi","hotelmapleregency","maple","regency"]},
    {"name": "Goan Hospitality –Goa Hotels & Resorts", "ga4_id": "391727033", "domain": "goanhospitality.com", "keywords": ["goan","goan hospitality  goa hotels   resorts","goanhospitality","hospitality"]},
    {"name": "Aditya Hometel, Ameerpet, Hyderabad", "ga4_id": "365046902", "domain": "adityahometel.com", "keywords": ["aditya","aditya hometel  ameerpet  hyderabad","adityahometel","ameerpet","hometel"]},
    {"name": "Swagath Group of Hotels", "ga4_id": "386963320", "domain": "swagathgroups.com", "keywords": ["swagath","swagath group of hotels","swagathgroups"]},
    {"name": "Hotel Park Avenue, Fort Kochi", "ga4_id": "386384288", "domain": "hotelparkavenuecochin.com", "keywords": ["avenue","fort","hotel park avenue  fort kochi","hotelparkavenuecochin","park"]},
    {"name": "Hotel Taj Plaza", "ga4_id": "387036459", "domain": "hoteltajplazaagra.com", "keywords": ["hotel taj plaza","hoteltajplazaagra","plaza","taj"]},
    {"name": "Hotel Ratnawali, Jaipur", "ga4_id": "390132959", "domain": "hotelratnawali.com", "keywords": ["hotel ratnawali  jaipur","hotelratnawali","ratnawali"]},
    {"name": "Hotel Shalimar - do not use", "ga4_id": "367151131", "domain": "hotel-shalimar.com", "keywords": ["hotel shalimar   do not use","hotel-shalimar","shalimar"]},
    {"name": "Hotel Marc Inn, Jaipur", "ga4_id": "364907752", "domain": "marcinn.com", "keywords": ["hotel marc inn  jaipur","marc","marcinn"]},
    {"name": "Hotel Jupiter, Manali", "ga4_id": "386470468", "domain": "hoteljupitermanali.co.in", "keywords": ["hotel jupiter  manali","hoteljupitermanali","jupiter","manali"]},
    {"name": "Hotel Malik Continental", "ga4_id": "367138690", "domain": "malikcontinental.com", "keywords": ["continental","hotel malik continental","malik","malikcontinental"]},
    {"name": "Hotel Ess Kay Ess Villa", "ga4_id": "361219926", "domain": "hotelsksvilla.com", "keywords": ["ess","hotel ess kay ess villa","hotelsksvilla","kay","villa"]},
    {"name": "Hotel Sarthak Palace, Karol Bagh, New Delhi", "ga4_id": "386346255", "domain": "hotelsarthakpalace.com", "keywords": ["bagh","hotel sarthak palace  karol bagh  new delhi","hotelsarthakpalace","karol","new","sarthak"]},
    {"name": "Kashish Residency & Banquet", "ga4_id": "386380135", "domain": "kashishresidency.com", "keywords": ["banquet","kashish","kashish residency   banquet","kashishresidency","residency"]},
    {"name": "Hotel Swaran Palace, Karol Bagh, New Delhi", "ga4_id": "387193298", "domain": "swaranpalace.com", "keywords": ["bagh","hotel swaran palace  karol bagh  new delhi","karol","new","swaran","swaranpalace"]},
    {"name": "Harbour View Residency", "ga4_id": "386411726", "domain": "harbourviewresidency.com", "keywords": ["harbour","harbour view residency","harbourviewresidency","residency","view"]},
    {"name": "Hotel Ashish Plaza, Pune", "ga4_id": "386339375", "domain": "hotelashishplaza.com", "keywords": ["ashish","hotel ashish plaza  pune","hotelashishplaza","plaza"]},
    {"name": "Hotel Ashiyana | Shivaji Nagar, Pune", "ga4_id": "386339375", "domain": "hotelashiyana.co.in", "keywords": ["ashiyana","hotel ashiyana   shivaji nagar  pune","hotelashiyana","nagar","shivaji"]},
    {"name": "Jaipur Residences", "ga4_id": "383937195", "domain": "jaipurresidences.com", "keywords": ["jaipur residences","jaipurresidences","residences"]},
    {"name": "Grand Resort", "ga4_id": "367445974", "domain": "grand-resort.co.in", "keywords": ["grand resort","grand-resort"]},
    {"name": "The Terminus", "ga4_id": "387244066", "domain": "theterminus.in", "keywords": ["terminus","the terminus","theterminus"]},
    {"name": "Hotel V M Residency, Vasant Kunj, Delhi", "ga4_id": "386308417", "domain": "vmresidency.net", "keywords": ["hotel v m residency  vasant kunj  delhi","kunj","residency","vasant","vmresidency"]},
    {"name": "Hotel Mareena Regency, Kochi", "ga4_id": "387213906", "domain": "mareenaregency.com", "keywords": ["hotel mareena regency  kochi","mareena","mareenaregency","regency"]},
    {"name": "Hotel Srinivas, Kochi", "ga4_id": "386577200", "domain": "hotel-srinivas.co.in", "keywords": ["hotel srinivas  kochi","hotel-srinivas","srinivas"]},
    {"name": "Hotel Hyderabad Grand, Shamshabad", "ga4_id": "386766642", "domain": "hotelhyderabadgrand.com", "keywords": ["hotel hyderabad grand  shamshabad","hotelhyderabadgrand","shamshabad"]},
    {"name": "The Silverline Hotel, Jessore Road, Kolkata Airport", "ga4_id": "386692919", "domain": "thesilverlinehotel.com", "keywords": ["airport","jessore","road","silverline","the silverline hotel  jessore road  kolkata airport","thesilverlinehotel"]},
    {"name": "Hotel Abaam, Kochi", "ga4_id": "386283569", "domain": "abaamhotels.com", "keywords": ["abaam","abaamhotels","hotel abaam  kochi"]},
    {"name": "Pearl Suites - A Boutique Hotel", "ga4_id": "386603987", "domain": "pearlsuites.in", "keywords": ["boutique","pearl","pearl suites   a boutique hotel","pearlsuites"]},
    {"name": "Palm Era Cottages, Coorg", "ga4_id": "386307935", "domain": "palmeracoorg.com", "keywords": ["coorg","cottages","era","palm","palm era cottages  coorg","palmeracoorg"]},
    {"name": "Ajay Guest House, Paharganj, Delhi", "ga4_id": "386534154", "domain": "unknown", "keywords": ["ajay","ajay guest house  paharganj  delhi","guest","house","paharganj"]},
    {"name": "The Studios at Solana Vacation Rental", "ga4_id": "386928725", "domain": "casasolana.com", "keywords": ["casasolana","rental","solana","studios","the studios at solana vacation rental","vacation"]},
    {"name": "Hotel Aadhar, Gurgaon", "ga4_id": "386467295", "domain": "unknown", "keywords": ["aadhar","gurgaon","hotel aadhar  gurgaon"]},
    {"name": "Emblem Hotel, New Friends Colony, New Delhi", "ga4_id": "387014393", "domain": "unknown", "keywords": ["colony","emblem","emblem hotel  new friends colony  new delhi","friends","new"]},
    {"name": "Hotel Benaka Suites, Hebbal, Bangalore", "ga4_id": "386106602", "domain": "benakasuites.com", "keywords": ["benaka","benakasuites","hebbal","hotel benaka suites  hebbal  bangalore"]},
    {"name": "Hotel Mayur, Gwalior", "ga4_id": "386802276", "domain": "hotelmayurgwalior.com", "keywords": ["gwalior","hotel mayur  gwalior","hotelmayurgwalior","mayur"]},
    {"name": "Shalimar Residency, Kochi", "ga4_id": "453310216", "domain": "shalimarresidency.com", "keywords": ["residency","shalimar","shalimar residency  kochi","shalimarresidency"]},
    {"name": "Shumbuk Homes Serviced Apartments, Gangtok", "ga4_id": "383716145", "domain": "shumbukhomes.com", "keywords": ["apartments","homes","serviced","shumbuk","shumbuk homes serviced apartments  gangtok","shumbukhomes"]},
    {"name": "Hotel Avana - do not use", "ga4_id": "387387423", "domain": "xxyz.co.in", "keywords": ["avana","hotel avana   do not use","xxyz"]},
    {"name": "Hotel Maruthi Residency Inn", "ga4_id": "386129901", "domain": "maruthiresidency.com", "keywords": ["hotel maruthi residency inn","maruthi","maruthiresidency","residency"]},
    {"name": "Hotel Summit, Ahmedabad", "ga4_id": "386710142", "domain": "hotelsummit.net", "keywords": ["ahmedabad","hotel summit  ahmedabad","hotelsummit","summit"]},
    {"name": "Hotel Classic Inn, Jaipur", "ga4_id": "387169390", "domain": "hotelclassicinn.com", "keywords": ["classic","hotel classic inn  jaipur","hotelclassicinn"]},
    {"name": "Hotel Noida International, Noida", "ga4_id": "386744119", "domain": "hotelnoidainternational.com", "keywords": ["hotel noida international  noida","hotelnoidainternational","international","noida"]},
    {"name": "The Lindsay", "ga4_id": "390901629", "domain": "unknown", "keywords": ["lindsay","the lindsay"]},
    {"name": "The Lindsay", "ga4_id": "387997837", "domain": "2895_simplotel.in", "keywords": ["2895_simplotel","lindsay","the lindsay"]},
    {"name": "Hotel Darshan Palace, Mysore", "ga4_id": "364913145", "domain": "hoteldarshanpalace.com", "keywords": ["darshan","hotel darshan palace  mysore","hoteldarshanpalace","mysore"]},
    {"name": "Hotel Niharika, Kolkata", "ga4_id": "386468230", "domain": "hotelniharika.in", "keywords": ["hotel niharika  kolkata","hotelniharika","niharika"]},
    {"name": "SAIACS CEO Centre, Bangalore", "ga4_id": "362370713", "domain": "saiacs-ceocenter.com", "keywords": ["centre","ceo","saiacs","saiacs ceo centre  bangalore","saiacs-ceocenter"]},
    {"name": "Hotel UD Residency, Basavanagagudi, Jayanagar, Bangalore", "ga4_id": "386981987", "domain": "udresidency.net", "keywords": ["basavanagagudi","hotel ud residency  basavanagagudi  jayanagar  bangalore","jayanagar","residency","udresidency"]},
    {"name": "Hotel Suraj, Pune", "ga4_id": "387242550", "domain": "hotelsuraj.in", "keywords": ["hotel suraj  pune","hotelsuraj","suraj"]},
    {"name": "Hotel Basera, Pune", "ga4_id": "386915159", "domain": "hotelbaserapune.com", "keywords": ["basera","hotel basera  pune","hotelbaserapune"]},
    {"name": "Hotel Olympia Inn, Aramgarh, Hyderabad", "ga4_id": "386666842", "domain": "hotelolympia.in", "keywords": ["aramgarh","hotel olympia inn  aramgarh  hyderabad","hotelolympia","olympia"]},
    {"name": "Davanam Sarovar Portico Suites - 4 Star Business Hotel In Bangalore", "ga4_id": "390831319", "domain": "davanamsarovarportico.com", "keywords": ["davanam","davanam sarovar portico suites   4 star business hotel in bangalore","davanamsarovarportico","portico","sarovar","star"]},
    {"name": "The Space Group", "ga4_id": "368614876", "domain": "livethespace.in", "keywords": ["livethespace","space","the space group"]},
    {"name": "Great Escapes Resort, Munnar", "ga4_id": "367225092", "domain": "germunnar.com", "keywords": ["escapes","germunnar","great","great escapes resort  munnar","munnar"]},
    {"name": "Bravo Beach Resort Siargao", "ga4_id": "386346725", "domain": "bravosiargao.com", "keywords": ["beach","bravo","bravo beach resort siargao","bravosiargao","siargao"]},
    {"name": "The Eternal Wave By Krish Retreat - Calangute, Goa", "ga4_id": "386827421", "domain": "eternalwave.in", "keywords": ["eternal","eternalwave","krish","retreat","the eternal wave by krish retreat   calangute  goa","wave"]},
    {"name": "Parampara Resort & Spa, Coorg, Kushalnagar", "ga4_id": "386683555", "domain": "unknown", "keywords": ["coorg","kushalnagar","parampara","parampara resort   spa  coorg  kushalnagar","spa"]},
    {"name": "Coorg Jungle Camp, Kushalnagar", "ga4_id": "387082734", "domain": "3436_simplotel.com", "keywords": ["3436_simplotel","camp","coorg","coorg jungle camp  kushalnagar","jungle","kushalnagar"]},
    {"name": "Hotel Natraj Manali (Pure Veg)***", "ga4_id": "386489068", "domain": "hotelnatrajmanali.co.in", "keywords": ["hotel natraj manali  pure veg","hotelnatrajmanali","manali","natraj","pure","veg"]},
    {"name": "Ramada Plaza by Wyndham Palm Grove", "ga4_id": "289687040", "domain": "ramadaplaza-juhu.com", "keywords": ["palm","plaza","ramada","ramada plaza by wyndham palm grove","ramadaplaza-juhu","wyndham"]},
    {"name": "Pakse Hotel & Restaurant, Champasak", "ga4_id": "364480580", "domain": "hotelpakse.com", "keywords": ["champasak","hotelpakse","pakse","pakse hotel   restaurant  champasak","restaurant"]},
    {"name": "Hotel Manali Continental, Manali", "ga4_id": "387219264", "domain": "hotelmanalicontinental.com", "keywords": ["continental","hotel manali continental  manali","hotelmanalicontinental","manali"]},
    {"name": "Hotel Maya Deluxe, MG Road, Secunderabad", "ga4_id": "386639311", "domain": "hotelmayadeluxe.in", "keywords": ["deluxe","hotel maya deluxe  mg road  secunderabad","hotelmayadeluxe","maya","road","secunderabad"]},
    {"name": "Tranzotel Airport Hotel Bangalore - DO NOT USE", "ga4_id": "392120446", "domain": "tranzotel.com", "keywords": ["airport","tranzotel","tranzotel airport hotel bangalore   do not use"]},
    {"name": "Hotel Trinity Corporate Suites, Sector 21, Gurgaon", "ga4_id": "386222330", "domain": "trinitycorporatesuites.com", "keywords": ["corporate","gurgaon","hotel trinity corporate suites  sector 21  gurgaon","sector","trinity","trinitycorporatesuites"]},
    {"name": "West Fort Hotel, Rajajinagar, Bangalore", "ga4_id": "387082616", "domain": "westforthotel.com", "keywords": ["fort","rajajinagar","west","west fort hotel  rajajinagar  bangalore","westforthotel"]},
    {"name": "Hotel Atithi - TGI Grand, Pondicherry", "ga4_id": "397917672", "domain": "atithipondicherry.com", "keywords": ["atithi","atithipondicherry","hotel atithi   tgi grand  pondicherry","pondicherry","tgi"]},
    {"name": "Hotel Atulyaa Taj, Agra", "ga4_id": "386598215", "domain": "hotelatulyaataj.in", "keywords": ["agra","atulyaa","hotel atulyaa taj  agra","hotelatulyaataj","taj"]},
    {"name": "Pals Inn, Patel Nagar, New Delhi", "ga4_id": "386481715", "domain": "palsinn.com", "keywords": ["nagar","new","pals","pals inn  patel nagar  new delhi","palsinn","patel"]},
    {"name": "Hablis Hotel Chennai", "ga4_id": "386107648", "domain": "hablis.com", "keywords": ["hablis","hablis hotel chennai"]},
    {"name": "Maharaja INN Chikmagalur", "ga4_id": "386185555", "domain": "mhjinn.co.in", "keywords": ["chikmagalur","maharaja","maharaja inn chikmagalur","mhjinn"]},
    {"name": "TGI Hotels and Resorts", "ga4_id": "388052695", "domain": "tgihotels.com", "keywords": ["tgi","tgi hotels and resorts","tgihotels"]},
    {"name": "Pace Hotels", "ga4_id": "367628248", "domain": "pace-hotels.com", "keywords": ["pace","pace hotels","pace-hotels"]},
    {"name": "Orchid Hotels", "ga4_id": "387713257", "domain": "orchidhotel.com", "keywords": ["orchid","orchid hotels","orchidhotel"]},
    {"name": "Heritage Hotels of Nainital", "ga4_id": "387081368", "domain": "himalayapavilion.com", "keywords": ["heritage","heritage hotels of nainital","himalayapavilion","nainital"]},
    {"name": "Hotel NM Royale County - Tripunithura, Kochi", "ga4_id": "386178732", "domain": "nmroyalecounty.com", "keywords": ["county","hotel nm royale county   tripunithura  kochi","nmroyalecounty","royale","tripunithura"]},
    {"name": "GenX Bhavnagar - DNU", "ga4_id": "392148900", "domain": "1589hotels-3774.com", "keywords": ["1589hotels-3774","bhavnagar","genx","genx bhavnagar   dnu"]},
    {"name": "Pride Hotels Group", "ga4_id": "392120468", "domain": "pridehotel.com", "keywords": ["pride","pride hotels group","pridehotel"]},
    {"name": "Raj Park Hotel Group", "ga4_id": "388055419", "domain": "rajpark.com", "keywords": ["park","raj","raj park hotel group","rajpark"]},
    {"name": "Clarks Group of Hotels", "ga4_id": "387517650", "domain": "hotelclarks.com", "keywords": ["clarks","clarks group of hotels","hotelclarks"]},
    {"name": "Neemrana Hotels", "ga4_id": "387144570", "domain": "neemranahotels.com", "keywords": ["neemrana","neemrana hotels","neemranahotels"]},
    {"name": "Amanvana Spa Resort - A Luxury Resort in Coorg", "ga4_id": "400277802", "domain": "amanvanaspa.com", "keywords": ["amanvana","amanvana spa resort   a luxury resort in coorg","amanvanaspa","coorg","luxury","spa"]},
    {"name": "The Retreat Hotel and Convention Centre", "ga4_id": "289770946", "domain": "retreat-mumbai.com", "keywords": ["centre","convention","retreat","retreat-mumbai","the retreat hotel and convention centre"]},
    {"name": "Nirmal Villa Group", "ga4_id": "367978074", "domain": "nirmalvilla.com", "keywords": ["nirmal","nirmal villa group","nirmalvilla","villa"]},
    {"name": "Hotel Trishul By T And M Hotels", "ga4_id": "469920597", "domain": "hoteltrishulharidwar.in", "keywords": ["hotel trishul by t and m hotels","hoteltrishulharidwar","trishul"]},
    {"name": "THREADMILL HOME LINEN", "ga4_id": "368208671", "domain": "threadmillhomelinen.com", "keywords": ["home","linen","threadmill","threadmill home linen","threadmillhomelinen"]},
    {"name": "Hotel Samson, Patnitop", "ga4_id": "386935360", "domain": "hotelsamson.in", "keywords": ["hotel samson  patnitop","hotelsamson","patnitop","samson"]},
    {"name": "Hotel Hari Piorko - Paharganj, New Delhi", "ga4_id": "384224790", "domain": "hotelharipiorkodelhi.com", "keywords": ["hari","hotel hari piorko   paharganj  new delhi","hotelharipiorkodelhi","new","paharganj","piorko"]},
    {"name": "Atrio by Devam", "ga4_id": "387020834", "domain": "atriohotels.com", "keywords": ["atrio","atrio by devam","atriohotels","devam"]},
    {"name": "The Earl's Court, Nainital", "ga4_id": "392129212", "domain": "theearlscourtnainital.in", "keywords": ["court","earl","nainital","the earl s court  nainital","theearlscourtnainital"]},
    {"name": "Sun n Snow Inn Hotel Kausani", "ga4_id": "389838707", "domain": "sunnsnowinnkausani.com", "keywords": ["kausani","snow","sun","sun n snow inn hotel kausani","sunnsnowinnkausani"]},
    {"name": "Adarsh Hamilton", "ga4_id": "386622403", "domain": "adarshhamilton.com", "keywords": ["adarsh","adarsh hamilton","adarshhamilton","hamilton"]},
    {"name": "Hotel Ritz Plaza, Amritsar", "ga4_id": "386095930", "domain": "ritzhotel.in", "keywords": ["amritsar","hotel ritz plaza  amritsar","plaza","ritz","ritzhotel"]},
    {"name": "Hill View Resorts", "ga4_id": "386555727", "domain": "hillviewresorts.in", "keywords": ["hill","hill view resorts","hillviewresorts","view"]},
    {"name": "Hotel Meghniwas, Jaipur", "ga4_id": "386217627", "domain": "meghniwas.com", "keywords": ["hotel meghniwas  jaipur","meghniwas"]},
    {"name": "Devnadi - The Heritage Hotel, Haridwar", "ga4_id": "368122257", "domain": "devnadi.in", "keywords": ["devnadi","devnadi   the heritage hotel  haridwar","haridwar","heritage"]},
    {"name": "The Onyx", "ga4_id": "386398589", "domain": "theonyx.in", "keywords": ["onyx","the onyx","theonyx"]},
    {"name": "Hill Country Hotels & Resorts India Ltd", "ga4_id": "386287863", "domain": "hillcountry.co.in", "keywords": ["country","hill","hill country hotels   resorts india ltd","hillcountry","india","ltd"]},
    {"name": "Sarovar Hotels Private Limited - India's Leading Hotel Chain", "ga4_id": "388013070", "domain": "sarovarhotels.com", "keywords": ["india","limited","private","sarovar","sarovar hotels private limited   india s leading hotel chain","sarovarhotels"]},
    {"name": "Devi Niketan Heritage Hotel, Jaipur", "ga4_id": "386694742", "domain": "deviniketan.com", "keywords": ["devi","devi niketan heritage hotel  jaipur","deviniketan","heritage","niketan"]},
    {"name": "Alps Resort, Dalhousie", "ga4_id": "347063824", "domain": "alpshoteldalhousie.com", "keywords": ["alps","alps resort  dalhousie","alpshoteldalhousie","dalhousie"]},
    {"name": "Wild Brook Retreat, Rajaji National Park", "ga4_id": "386380377", "domain": "wildbrookretreat.com", "keywords": ["brook","rajaji","retreat","wild","wild brook retreat  rajaji national park","wildbrookretreat"]},
    {"name": "Corbett Wild Iris Spa & Resort, Ramnagar", "ga4_id": "387179194", "domain": "irisresorts.com", "keywords": ["corbett","corbett wild iris spa   resort  ramnagar","iris","irisresorts","spa","wild"]},
    {"name": "Ras Resort by Treat", "ga4_id": "387133914", "domain": "rasresorts.com", "keywords": ["ras","ras resort by treat","rasresorts","treat"]},
    {"name": "Hotel Saffron Leaf, Dehradun", "ga4_id": "387031060", "domain": "saffronleaf.com", "keywords": ["dehradun","hotel saffron leaf  dehradun","leaf","saffron","saffronleaf"]},
    {"name": "The Hamuse Hotel Kodaikanal - Luxury Redefined", "ga4_id": "386856491", "domain": "thehamusehotel.com", "keywords": ["hamuse","kodaikanal","luxury","redefined","the hamuse hotel kodaikanal   luxury redefined","thehamusehotel"]},
    {"name": "Renai Hospitality & Healthcare", "ga4_id": "365427749", "domain": "renaicochin.in", "keywords": ["healthcare","hospitality","renai","renai hospitality   healthcare","renaicochin"]},
    {"name": "Sanctum Suites Bengaluru", "ga4_id": "326512323", "domain": "thesanctumsuites.com", "keywords": ["bengaluru","sanctum","sanctum suites bengaluru","thesanctumsuites"]},
    {"name": "Hotel Jyoti - Rajkot, Gujarat", "ga4_id": "386764204", "domain": "hoteljyoti.net", "keywords": ["gujarat","hotel jyoti   rajkot  gujarat","hoteljyoti","jyoti","rajkot"]},
    {"name": "The Hans Hotel, Hubli", "ga4_id": "380728689", "domain": "thehanshotel.com", "keywords": ["hans","hubli","the hans hotel  hubli","thehanshotel"]},
    {"name": "Kohinoor Hotels", "ga4_id": "386242336", "domain": "kohinoorhotels.com", "keywords": ["kohinoor","kohinoor hotels","kohinoorhotels"]},
    {"name": "Summit Hotels & Resorts", "ga4_id": "390937652", "domain": "summithotels.in", "keywords": ["summit","summit hotels   resorts","summithotels"]},
    {"name": "JP Hotel Chennai", "ga4_id": "386355781", "domain": "hoteljpchennai.com", "keywords": ["hoteljpchennai","jp hotel chennai"]},
    {"name": "Sai Priya Beach Resort, Vizag", "ga4_id": "387018446", "domain": "saipriyabeachresorts.com", "keywords": ["beach","priya","sai","sai priya beach resort  vizag","saipriyabeachresorts","vizag"]},
    {"name": "E Hotel, Chennai", "ga4_id": "384650260", "domain": "emallhotel.com", "keywords": ["e hotel  chennai","emallhotel"]},
    {"name": "V Hotel - Srinagar, Vishakhapatnam", "ga4_id": "386576885", "domain": "hotelv.in", "keywords": ["hotelv","srinagar","v hotel   srinagar  vishakhapatnam","vishakhapatnam"]},
    {"name": "The Heron, Nairobi", "ga4_id": "453327248", "domain": "heronhotel.com", "keywords": ["heron","heronhotel","nairobi","the heron  nairobi"]},
    {"name": "Hotel Southern - New Delhi & Vijayawada", "ga4_id": "392167441", "domain": "hotelsouthern.com", "keywords": ["hotel southern   new delhi   vijayawada","hotelsouthern","new","southern","vijayawada"]},
    {"name": "Hotel Southern Grand - Vijayawada", "ga4_id": "395520345", "domain": "hotelsoutherngrand.com", "keywords": ["hotel southern grand   vijayawada","hotelsoutherngrand","southern","vijayawada"]},
    {"name": "Kalyan Residency Hotel in Tirupati", "ga4_id": "386573190", "domain": "kalyanresidency.com", "keywords": ["kalyan","kalyan residency hotel in tirupati","kalyanresidency","residency","tirupati"]},
    {"name": "Mount Hotels", "ga4_id": "386684255", "domain": "mounthotels.in", "keywords": ["mount","mount hotels","mounthotels"]},
    {"name": "Trinity Suites - Budget Hotel, Bangalore", "ga4_id": "367541003", "domain": "trinitysuites.in", "keywords": ["budget","trinity","trinity suites   budget hotel  bangalore","trinitysuites"]},
    {"name": "Ibbanicadu Estate Homestay, Coorg", "ga4_id": "367602055", "domain": "ibbanicadu-homestay.com", "keywords": ["coorg","estate","homestay","ibbanicadu","ibbanicadu estate homestay  coorg","ibbanicadu-homestay"]},
    {"name": "Pushpak Resort, Shirdi - A Division Of  G.S. Kote Patil Ent. Pvt. Ltd.", "ga4_id": "386789230", "domain": "hotelpushpakresort.com", "keywords": ["division","hotelpushpakresort","kote","pushpak","pushpak resort  shirdi   a division of  g s  kote patil ent  pvt  ltd","shirdi"]},
    {"name": "Xandari Hotels, Kerala", "ga4_id": "321364499", "domain": "xandari.com", "keywords": ["kerala","xandari","xandari hotels  kerala"]},
    {"name": "Presidency Hotels - Bangalore", "ga4_id": "386995509", "domain": "hotelpresidencyblr.com", "keywords": ["hotelpresidencyblr","presidency","presidency hotels   bangalore"]},
    {"name": "Shaheen Bagh - A Luxury Boutique Resort & Spa in Dehradun", "ga4_id": "380355944", "domain": "shaheenbagh.in", "keywords": ["bagh","boutique","luxury","shaheen","shaheen bagh   a luxury boutique resort   spa in dehradun","shaheenbagh"]},
    {"name": "The Golden Tusk, Jim Corbett", "ga4_id": "364992257", "domain": "thegoldentusk.com", "keywords": ["corbett","golden","jim","the golden tusk  jim corbett","thegoldentusk","tusk"]},
    {"name": "Chariot Beach Resorts, Mahabalipuram, Chennai", "ga4_id": "387115049", "domain": "chariotbeachresorts.com", "keywords": ["beach","chariot","chariot beach resorts  mahabalipuram  chennai","chariotbeachresorts","mahabalipuram"]},
    {"name": "Daspalla Hotels", "ga4_id": "387007005", "domain": "daspallahotels.com", "keywords": ["daspalla","daspalla hotels","daspallahotels"]},
    {"name": "Natai Beach Resort", "ga4_id": "365666357", "domain": "natairesort.com", "keywords": ["beach","natai","natai beach resort","natairesort"]},
    {"name": "Nice Guest House", "ga4_id": "386307476", "domain": "niceguesthouse.in", "keywords": ["guest","house","nice","nice guest house","niceguesthouse"]},
    {"name": "Hotel Southern Regency, Karol Bagh, Delhi", "ga4_id": "390296379", "domain": "southernregency.com", "keywords": ["bagh","hotel southern regency  karol bagh  delhi","karol","regency","southern","southernregency"]},
    {"name": "SRM Hotel Pvt Ltd", "ga4_id": "386248003", "domain": "srmhotels.com", "keywords": ["ltd","pvt","srm","srm hotel pvt ltd","srmhotels"]},
    {"name": "Jehan Numa Hotels", "ga4_id": "330849884", "domain": "jehannuma.com", "keywords": ["jehan","jehan numa hotels","jehannuma","numa"]},
    {"name": "Taurus Sarovar Portico, New Delhi", "ga4_id": "365819940", "domain": "taurushotels.com", "keywords": ["new","portico","sarovar","taurus","taurus sarovar portico  new delhi","taurushotels"]},
    {"name": "Le Dupleix, Pondicherry", "ga4_id": "367313582", "domain": "ledupleix.com", "keywords": ["dupleix","le dupleix  pondicherry","ledupleix","pondicherry"]},
    {"name": "Shri Radha Brij Vasundhara Resort & Spa, Mathura", "ga4_id": "387257417", "domain": "shriradhabrijvasundhara.co", "keywords": ["brij","radha","shri","shri radha brij vasundhara resort   spa  mathura","shriradhabrijvasundhara","vasundhara"]},
    {"name": "Owl and the Pussycat Hotel in Galle", "ga4_id": "399539686", "domain": "otphotel.com", "keywords": ["galle","otphotel","owl","owl and the pussycat hotel in galle","pussycat"]},
    {"name": "Hotel Saket 27, New Delhi", "ga4_id": "386208344", "domain": "saket27.com", "keywords": ["hotel saket 27  new delhi","new","saket","saket27"]},
    {"name": "Ashray Inn Hotels, Ahmedabad", "ga4_id": "387219486", "domain": "ashrayinnhotels.com", "keywords": ["ahmedabad","ashray","ashray inn hotels  ahmedabad","ashrayinnhotels"]},
    {"name": "Neelkanth Sarovar Premiere Lusaka", "ga4_id": "365285875", "domain": "neelkanthsarovarpremiere.com", "keywords": ["lusaka","neelkanth","neelkanth sarovar premiere lusaka","neelkanthsarovarpremiere","premiere","sarovar"]},
    {"name": "Pramod Hotels & Resorts", "ga4_id": "365128808", "domain": "pramodresorts.com", "keywords": ["pramod","pramod hotels   resorts","pramodresorts"]},
    {"name": "Gobinddham Rooms, Mumbai", "ga4_id": "387539009", "domain": "gobinddham-4853.in", "keywords": ["gobinddham","gobinddham rooms  mumbai","gobinddham-4853","rooms"]},
    {"name": "JRD Hotels", "ga4_id": "386208792", "domain": "jrdhotels.com", "keywords": ["jrd","jrd hotels","jrdhotels"]},
    {"name": "Piccadily Hotels", "ga4_id": "386858785", "domain": "piccadily.co.in", "keywords": ["piccadily","piccadily hotels"]},
    {"name": "The PL Palace Hotel, Agra", "ga4_id": "386902776", "domain": "plpalacehotels.com", "keywords": ["agra","plpalacehotels","the pl palace hotel  agra"]},
    {"name": "The Zehneria, Nairobi", "ga4_id": "453320270", "domain": "zehneriahotel.com", "keywords": ["nairobi","the zehneria  nairobi","zehneria","zehneriahotel"]},
    {"name": "Infinity Resorts", "ga4_id": "386864305", "domain": "infinityresorts.com", "keywords": ["infinity","infinity resorts","infinityresorts"]},
    {"name": "Rosakue Hospitality", "ga4_id": "320671192", "domain": "rosakue2.com", "keywords": ["hospitality","rosakue","rosakue hospitality","rosakue2"]},
    {"name": "Dragonfly Hotels & Service Apartments, Andheri, Mumbai", "ga4_id": "387586160", "domain": "dragonflyhotel.in", "keywords": ["andheri","apartments","dragonfly","dragonfly hotels   service apartments  andheri  mumbai","dragonflyhotel","service"]},
    {"name": "Rockland Hotels, New Delhi", "ga4_id": "386376743", "domain": "rocklandhotels.com", "keywords": ["new","rockland","rockland hotels  new delhi","rocklandhotels"]},
    {"name": "Envotel by The Orchid", "ga4_id": "387757257", "domain": "envotel.in", "keywords": ["envotel","envotel by the orchid","orchid"]},
    {"name": "Parampara Residency, Coorg", "ga4_id": "386935347", "domain": "unknown", "keywords": ["coorg","parampara","parampara residency  coorg","residency"]},
    {"name": "Colonel's Retreat Hotels", "ga4_id": "366288310", "domain": "colonelsretreat.com", "keywords": ["colonel","colonel s retreat hotels","colonelsretreat","retreat"]},
    {"name": "Abad Hotels", "ga4_id": "391316947", "domain": "abadhotels.com", "keywords": ["abad","abad hotels","abadhotels"]},
    {"name": "The Waverly Hotel & Residences", "ga4_id": "386653003", "domain": "thewaverly.in", "keywords": ["residences","the waverly hotel   residences","thewaverly","waverly"]},
    {"name": "GK Hill View Resort", "ga4_id": "386159731", "domain": "gkhvresort.com", "keywords": ["gk hill view resort","gkhvresort","hill","view"]},
    {"name": "Zara's Resort, Khandala", "ga4_id": "387186932", "domain": "zarasresort.com", "keywords": ["khandala","zara","zara s resort  khandala","zarasresort"]},
    {"name": "Casa Legend Goa", "ga4_id": "386144060", "domain": "casalegendgoa.com", "keywords": ["casa","casa legend goa","casalegendgoa","legend"]},
    {"name": "The Bristol Hotel, Gurgaon", "ga4_id": "386864167", "domain": "thebristolhotel.in", "keywords": ["bristol","gurgaon","the bristol hotel  gurgaon","thebristolhotel"]},
    {"name": "BluPetal Hotel", "ga4_id": "402581556", "domain": "blupetalhotel.com", "keywords": ["blupetal","blupetal hotel","blupetalhotel"]},
    {"name": "The Serai", "ga4_id": "377398520", "domain": "theserai.in", "keywords": ["serai","the serai","theserai"]},
    {"name": "Hotel Kanha Shyam, Prayagraj", "ga4_id": "387117431", "domain": "hotelkanhashyam.com", "keywords": ["hotel kanha shyam  prayagraj","hotelkanhashyam","kanha","prayagraj","shyam"]},
    {"name": "Galleu Hill Resort", "ga4_id": "411350967", "domain": "5104_simplotel.com", "keywords": ["5104_simplotel","galleu","galleu hill resort","hill"]},
    {"name": "Woodays Resort, Shimla", "ga4_id": "386393816", "domain": "woodaysresorts.com", "keywords": ["shimla","woodays","woodays resort  shimla","woodaysresorts"]},
    {"name": "Tendu Leaf Jungle Resort & Spa", "ga4_id": "386797691", "domain": "tenduleafjungleresort.com", "keywords": ["jungle","leaf","spa","tendu","tendu leaf jungle resort   spa","tenduleafjungleresort"]},
    {"name": "Nature Trails Resorts", "ga4_id": "396582644", "domain": "naturetrails.in", "keywords": ["nature","nature trails resorts","naturetrails","trails"]},
    {"name": "Hotel Polo Max(Redirects)", "ga4_id": "391613981", "domain": "hotelpolomaxabdullah.com", "keywords": ["hotel polo max redirects","hotelpolomaxabdullah","max","polo"]},
    {"name": "Hotel Rio Meridian", "ga4_id": "401116793", "domain": "riomeridianhotels.com", "keywords": ["hotel rio meridian","meridian","rio","riomeridianhotels"]},
    {"name": "Orbett Hotel", "ga4_id": "402578479", "domain": "orbetthotels.com", "keywords": ["orbett","orbett hotel","orbetthotels"]},
    {"name": "Purple Cloud Hotels", "ga4_id": "366621407", "domain": "purplecloudhotels.com", "keywords": ["cloud","purple","purple cloud hotels","purplecloudhotels"]},
    {"name": "Black Thunder - Water Theme Park", "ga4_id": "386522507", "domain": "blackthunder.in", "keywords": ["black","black thunder   water theme park","blackthunder","theme","thunder","water"]},
    {"name": "Sapphire Club", "ga4_id": "386293841", "domain": "sapphire.club", "keywords": ["club","sapphire","sapphire club"]},
    {"name": "Hotel Karthika Park, Kazhakuttam", "ga4_id": "386686691", "domain": "hotelkarthikapark.com", "keywords": ["hotel karthika park  kazhakuttam","hotelkarthikapark","karthika","kazhakuttam","park"]},
    {"name": "Barefoot Scuba Resort", "ga4_id": "386586562", "domain": "barefootscuba.in", "keywords": ["barefoot","barefoot scuba resort","barefootscuba","scuba"]},
    {"name": "Barefoot at Havelock", "ga4_id": "392146132", "domain": "barefoot-andaman.com", "keywords": ["barefoot","barefoot at havelock","barefoot-andaman","havelock"]},
    {"name": "Temple Tree Hotel, Bangalore", "ga4_id": "387097041", "domain": "templetreehotel.com", "keywords": ["temple","temple tree hotel  bangalore","templetreehotel","tree"]},
    {"name": "Riverstone Cottages, Dehradun", "ga4_id": "386195960", "domain": "riverstonecottages.com", "keywords": ["cottages","dehradun","riverstone","riverstone cottages  dehradun","riverstonecottages"]},
    {"name": "Hotel Orritel west", "ga4_id": "402582456", "domain": "orritel.com", "keywords": ["hotel orritel west","orritel","west"]},
    {"name": "Amara Hotels and Resorts", "ga4_id": "503924305", "domain": "amararesorts.com", "keywords": ["amara","amara hotels and resorts","amararesorts"]},
    {"name": "Bamboo Saa Resort & Spa, Udaipur", "ga4_id": "287972673", "domain": "unknown", "keywords": ["bamboo","bamboo saa resort   spa  udaipur","saa","spa","udaipur"]},
    {"name": "Best Western Premier Westlands", "ga4_id": "504145965", "domain": "bwpremierwestlands.com", "keywords": ["best","best western premier westlands","bwpremierwestlands","premier","western","westlands"]},
    {"name": "Mint Hotels - Leading Chain of Hotels & Resorts", "ga4_id": "386247999", "domain": "staymint.com", "keywords": ["chain","leading","mint","mint hotels   leading chain of hotels   resorts","staymint"]},
    {"name": "S Hotels Jamaica", "ga4_id": "452223282", "domain": "shotelsjamaica.com", "keywords": ["jamaica","s hotels jamaica","shotelsjamaica"]},
    {"name": "Crimson Lotus, Bangalore", "ga4_id": "365782794", "domain": "crimsonlotus.in", "keywords": ["crimson","crimson lotus  bangalore","crimsonlotus","lotus"]},
    {"name": "The Mansion House, Alibaug", "ga4_id": "386984168", "domain": "themansionhousealibaug.com", "keywords": ["alibaug","house","mansion","the mansion house  alibaug","themansionhousealibaug"]},
    {"name": "Lamari Siargao", "ga4_id": "366229907", "domain": "lamarisiargao.com", "keywords": ["lamari","lamari siargao","lamarisiargao","siargao"]},
    {"name": "Hotel Altitude, Coorg", "ga4_id": "386301458", "domain": "5455_simplotel.com", "keywords": ["5455_simplotel","altitude","coorg","hotel altitude  coorg"]},
    {"name": "The Highland Park, Manali", "ga4_id": "386318453", "domain": "thehighlandpark.in", "keywords": ["highland","manali","park","the highland park  manali","thehighlandpark"]},
    {"name": "Icon Hotels India by Bhagini", "ga4_id": "467093729", "domain": "iconhotelsindia.com", "keywords": ["bhagini","icon","icon hotels india by bhagini","iconhotelsindia","india"]},
    {"name": "Ananta Hotels & Resorts", "ga4_id": "391269303", "domain": "anantahotels.com", "keywords": ["ananta","ananta hotels   resorts","anantahotels"]},
    {"name": "Caravela Beach Resort Goa", "ga4_id": "391611760", "domain": "caravelabeachresortgoa.com", "keywords": ["beach","caravela","caravela beach resort goa","caravelabeachresortgoa"]},
    {"name": "3102bce - A Vedic Resort by Lindsay", "ga4_id": "387184944", "domain": "fwef", "keywords": ["3102bce","3102bce   a vedic resort by lindsay","fwef","lindsay","vedic"]},
    {"name": "Water Kingdom", "ga4_id": "378387392", "domain": "waterkingdom.in", "keywords": ["kingdom","water","water kingdom","waterkingdom"]},
    {"name": "Hotel Le Grande - Mumbai International Airport", "ga4_id": "386161977", "domain": "hotellegrande.com", "keywords": ["airport","grande","hotel le grande   mumbai international airport","hotellegrande","international"]},
    {"name": "Hotel Polo Towers", "ga4_id": "527604567", "domain": "polo.polohotelsandresorts.com", "keywords": ["hotel polo towers","polo","towers"]},
    {"name": "Hotel Golden Castle", "ga4_id": "402694069", "domain": "hotelgoldencastle.com", "keywords": ["castle","golden","hotel golden castle","hotelgoldencastle"]},
    {"name": "Symphony Resorts", "ga4_id": "386516134", "domain": "symphonyresorts.com", "keywords": ["symphony","symphony resorts","symphonyresorts"]},
    {"name": "UDS Group of Hotels", "ga4_id": "373789108", "domain": "udshotels.com", "keywords": ["uds","uds group of hotels","udshotels"]},
    {"name": "Hotel Avora Tree", "ga4_id": "386294841", "domain": "avoratree.com", "keywords": ["avora","avoratree","hotel avora tree","tree"]},
    {"name": "The Tattva Boutique Resort (OLD)", "ga4_id": "365674566", "domain": "thetattva.co.in", "keywords": ["boutique","old","tattva","the tattva boutique resort  old","thetattva"]},
    {"name": "Theory9 - Premium Service Apts", "ga4_id": "467131587", "domain": "theory9.in", "keywords": ["apts","premium","service","theory9","theory9   premium service apts"]},
    {"name": "Jenneys Residency, Coimbatore", "ga4_id": "386226345", "domain": "jenneyresidency.in", "keywords": ["coimbatore","jenneyresidency","jenneys","jenneys residency  coimbatore","residency"]},
    {"name": "Heritage Village Resorts & Spa", "ga4_id": "401519953", "domain": "heritagevillageresorts.com", "keywords": ["heritage","heritage village resorts   spa","heritagevillageresorts","spa","village"]},
    {"name": "Caravela Beach Resort - Investor relation - Redirect", "ga4_id": "391830423", "domain": "investors.caravelabeachresortgoa.com", "keywords": ["beach","caravela","caravela beach resort   investor relation   redirect","investor","investors","relation"]},
    {"name": "TreeHouse Hotels, Resorts & Serviced Apartments", "ga4_id": "402559233", "domain": "treehousehotels.in", "keywords": ["apartments","serviced","treehouse","treehouse hotels  resorts   serviced apartments","treehousehotels"]},
    {"name": "The Regnant", "ga4_id": "386123264", "domain": "theregnant.in", "keywords": ["regnant","the regnant","theregnant"]},
    {"name": "Caravela Beach Resort, Goa", "ga4_id": "391868124", "domain": "offers.caravelabeachresortgoa.com", "keywords": ["beach","caravela","caravela beach resort  goa","offers"]},
    {"name": "Tropicana Resort & Spa, Alibaug", "ga4_id": "367874211", "domain": "tropicanaalibaug.com", "keywords": ["alibaug","spa","tropicana","tropicana resort   spa  alibaug","tropicanaalibaug"]},
    {"name": "Barefoot Scuba", "ga4_id": "391810572", "domain": "voucher.barefootscuba.in", "keywords": ["barefoot","barefoot scuba","scuba","voucher"]},
    {"name": "Royal Orchid & Regenta Hotels", "ga4_id": "257421292", "domain": "royalorchidhotels.com", "keywords": ["orchid","regenta","royal","royal orchid   regenta hotels","royalorchidhotels"]},
    {"name": "Barefoot Scuba", "ga4_id": "364683372", "domain": "activity.barefootscuba.in", "keywords": ["activity","barefoot","barefoot scuba","scuba"]},
    {"name": "Lulung Aranya Nivas Resort (Managed by Silverpine Hospitality Pvt. Ltd.)", "ga4_id": "367781318", "domain": "simlipalforestresort.com", "keywords": ["aranya","lulung","lulung aranya nivas resort  managed by silverpine hospitality pvt  ltd","managed","nivas","simlipalforestresort"]},
    {"name": "Combermere Shimla", "ga4_id": "387173814", "domain": "hotelcombermere.com", "keywords": ["combermere","combermere shimla","hotelcombermere","shimla"]},
    {"name": "Hotel Marina Shimla", "ga4_id": "386332112", "domain": "marinashimla.com", "keywords": ["hotel marina shimla","marina","marinashimla","shimla"]},
    {"name": "The Saibaba Hotel", "ga4_id": "386720053", "domain": "thesaibabahotel.com", "keywords": ["saibaba","the saibaba hotel","thesaibabahotel"]},
    {"name": "Coral Reef Hotel & Resort", "ga4_id": "387142703", "domain": "coralreefandaman.com", "keywords": ["coral","coral reef hotel   resort","coralreefandaman","reef"]},
    {"name": "Neemrana's Glasshouse on The Ganges - 21st Century, Rishikesh", "ga4_id": "387144570", "domain": "glasshouseontheganges.neemranahotels.com", "keywords": ["21st","ganges","glasshouse","glasshouseontheganges","neemrana","neemrana s glasshouse on the ganges   21st century  rishikesh"]},
    {"name": "Rivido Hotels & Resorts", "ga4_id": "386596180", "domain": "rividohotels.in", "keywords": ["rivido","rivido hotels   resorts","rividohotels"]},
    {"name": "Hotel Monarch International", "ga4_id": "386814213", "domain": "hotelmonarch.in", "keywords": ["hotel monarch international","hotelmonarch","international","monarch"]},
    {"name": "Tadhana Villa", "ga4_id": "386346725", "domain": "bravosiargao.com", "keywords": ["bravosiargao","tadhana","tadhana villa","villa"]},
    {"name": "Ramada by Wyndham Addis, Addis Ababa", "ga4_id": "391543759", "domain": "ramadaaddis.com", "keywords": ["addis","ramada","ramada by wyndham addis  addis ababa","ramadaaddis","wyndham"]},
    {"name": "The Manor Luxury Apartments, Shimla", "ga4_id": "386685208", "domain": "themanornaldehra.com", "keywords": ["apartments","luxury","manor","shimla","the manor luxury apartments  shimla","themanornaldehra"]},
    {"name": "Living Room Hotels and Resorts by Seasons", "ga4_id": "386105355", "domain": "livingroomhotels.in", "keywords": ["living","living room hotels and resorts by seasons","livingroomhotels","room","seasons"]},
    {"name": "Night Hotel Broadway- Do Not Use", "ga4_id": "386971556", "domain": "nighthotelbroadway.com", "keywords": ["broadway","night","night hotel broadway  do not use","nighthotelbroadway"]},
    {"name": "Rockski Boutique Bed and Breakfast", "ga4_id": "508958664", "domain": "rockskibnb.com", "keywords": ["bed","boutique","breakfast","rockski","rockski boutique bed and breakfast","rockskibnb"]},
    {"name": "Temple Tree Hotel Shirdi", "ga4_id": "386806575", "domain": "hoteltempletree.com", "keywords": ["hoteltempletree","shirdi","temple","temple tree hotel shirdi","tree"]},
    {"name": "LETS CAMP", "ga4_id": "379039396", "domain": "lets.co.in", "keywords": ["camp","lets","lets camp"]},
    {"name": "Grand Gardenia, Tiruchirappalli", "ga4_id": "386130309", "domain": "grandgardenia.com", "keywords": ["gardenia","grand gardenia  tiruchirappalli","grandgardenia","tiruchirappalli"]},
    {"name": "Hotel Grand Galaxy, Chennai", "ga4_id": "387200819", "domain": "grandgalaxy.in", "keywords": ["galaxy","grandgalaxy","hotel grand galaxy  chennai"]},
    {"name": "IRA Hotels", "ga4_id": "383732888", "domain": "irahotels.com", "keywords": ["ira","ira hotels","irahotels"]},
    {"name": "Grand Arcadia, Tiruchirappalli", "ga4_id": "387100167", "domain": "grandarcadia.com", "keywords": ["arcadia","grand arcadia  tiruchirappalli","grandarcadia","tiruchirappalli"]},
    {"name": "Mittal Gardens", "ga4_id": "387149853", "domain": "themittalgardens.com", "keywords": ["gardens","mittal","mittal gardens","themittalgardens"]},
    {"name": "Hotel Uday Palace", "ga4_id": "364828513", "domain": "hoteludaypalace.net", "keywords": ["hotel uday palace","hoteludaypalace","uday"]},
    {"name": "Karwaan Jaisalmer", "ga4_id": "390979434", "domain": "karwaanresorts.com", "keywords": ["jaisalmer","karwaan","karwaan jaisalmer","karwaanresorts"]},
    {"name": "Karma Lakelands", "ga4_id": "386730458", "domain": "karmalakelands.com", "keywords": ["karma","karma lakelands","karmalakelands","lakelands"]},
    {"name": "Bird Park - EsselWorld", "ga4_id": "390286964", "domain": "esselworldbirdpark.in", "keywords": ["bird","bird park   esselworld","esselworld","esselworldbirdpark","park"]},
    {"name": "Hotel Paras Heights", "ga4_id": "386221834", "domain": "hotelparasheights.com", "keywords": ["heights","hotel paras heights","hotelparasheights","paras"]},
    {"name": "Ascot Hospitality", "ga4_id": "392168766", "domain": "ascothospitality.in", "keywords": ["ascot","ascot hospitality","ascothospitality","hospitality"]},
    {"name": "Hotel Mount View", "ga4_id": "392128300", "domain": "hotelmountview.com", "keywords": ["hotel mount view","hotelmountview","mount","view"]},
    {"name": "Lilac Hotels", "ga4_id": "280112957", "domain": "lilachotels.com", "keywords": ["lilac","lilac hotels","lilachotels"]},
    {"name": "Aramness", "ga4_id": "467754173", "domain": "aramness.com", "keywords": ["aramness"]},
    {"name": "Hotel Goverdhan, Agra", "ga4_id": "387245053", "domain": "goverdhanhotel.com", "keywords": ["agra","goverdhan","goverdhanhotel","hotel goverdhan  agra"]},
    {"name": "Marasa Hospitality", "ga4_id": "386785113", "domain": "marasaindia.com", "keywords": ["hospitality","marasa","marasa hospitality","marasaindia"]},
    {"name": "Hotel Home In (Sonipat)", "ga4_id": "391832193", "domain": "hotelhomein.com", "keywords": ["home","hotel home in  sonipat","hotelhomein","sonipat"]},
    {"name": "FERRO CONCRETE CONSTRUCTION (I) PVT. LTD.", "ga4_id": "367932064", "domain": "ferroconcrete.in", "keywords": ["concrete","construction","ferro","ferro concrete construction  i  pvt  ltd","ferroconcrete","pvt"]},
    {"name": "Hotel Signature Airport Zone Shamshabad Hyderabad", "ga4_id": "386733863", "domain": "signatureairportzone.com", "keywords": ["airport","hotel signature airport zone shamshabad hyderabad","shamshabad","signature","signatureairportzone","zone"]},
    {"name": "Hotel Saar Inn", "ga4_id": "396985030", "domain": "saarinn.com", "keywords": ["hotel saar inn","saar","saarinn"]},
    {"name": "Amrapali Grand", "ga4_id": "397010031", "domain": "amrapalihotel.com", "keywords": ["amrapali","amrapali grand","amrapalihotel"]},
    {"name": "Simplotel", "ga4_id": "375525753", "domain": "simplotel.com", "keywords": ["simplotel"]},
    {"name": "Singge Hotels - EXParent (DNU)", "ga4_id": "386170769", "domain": "singgehotels.in", "keywords": ["exparent","singge","singge hotels   exparent  dnu","singgehotels"]},
    {"name": "Hotel Singge Palace", "ga4_id": "482942819", "domain": "singgehotels.com", "keywords": ["hotel singge palace","singge","singgehotels"]},
    {"name": "Brij Hotels", "ga4_id": "382610238", "domain": "brijhotels.com", "keywords": ["brij","brij hotels","brijhotels"]},
    {"name": "Altamont Court", "ga4_id": "386282594", "domain": "altamontcourt.com", "keywords": ["altamont","altamont court","altamontcourt","court"]},
    {"name": "Manas Lifestyle Resort", "ga4_id": "396992238", "domain": "manaslifestyleresort.in", "keywords": ["lifestyle","manas","manas lifestyle resort","manaslifestyleresort"]},
    {"name": "Mystic Valley Spa Resort", "ga4_id": "360132490", "domain": "mysticvalleyresort.in", "keywords": ["mystic","mystic valley spa resort","mysticvalleyresort","spa","valley"]},
    {"name": "Noormahal Palace", "ga4_id": "395970136", "domain": "noormahalpalace.com", "keywords": ["noormahal","noormahal palace","noormahalpalace"]},
    {"name": "The Tamara Resorts", "ga4_id": "277912055", "domain": "thetamara.com", "keywords": ["tamara","the tamara resorts","thetamara"]},
    {"name": "Silver Sand Hotels & Resorts", "ga4_id": "386702542", "domain": "silversandhotels.com", "keywords": ["sand","silver","silver sand hotels   resorts","silversandhotels"]},
    {"name": "The Manohar, Hyderabad", "ga4_id": "386573408", "domain": "themanohar.com", "keywords": ["manohar","the manohar  hyderabad","themanohar"]},
    {"name": "Istana Resort and Spa by Sagar", "ga4_id": "386965058", "domain": "thesagarhotels.com", "keywords": ["istana","istana resort and spa by sagar","sagar","spa","thesagarhotels"]},
    {"name": "Night Hotel Bangkok", "ga4_id": "395540853", "domain": "nighthotels.com", "keywords": ["bangkok","night","night hotel bangkok","nighthotels"]},
    {"name": "Caravela Beach Resort Goa- DO NOT USE- and Do not Inactive this shell.", "ga4_id": "391611760", "domain": "caravelabeachresortgoa.com", "keywords": ["beach","caravela","caravela beach resort goa  do not use  and do not inactive this shell","caravelabeachresortgoa","inactive","this"]},
    {"name": "The Lalita Grand Mathura - Vrindavan", "ga4_id": "386328770", "domain": "lalitagrand.com", "keywords": ["lalita","lalitagrand","mathura","the lalita grand mathura   vrindavan","vrindavan"]},
    {"name": "EasyChair Hospitality", "ga4_id": "386628592", "domain": "easychairhospitality.com", "keywords": ["easychair","easychair hospitality","easychairhospitality","hospitality"]},
    {"name": "Agate Hospitality", "ga4_id": "367542438", "domain": "agatehotels.com", "keywords": ["agate","agate hospitality","agatehotels","hospitality"]},
    {"name": "Udman Hotels & Resorts", "ga4_id": "387148232", "domain": "udmanhotels.com", "keywords": ["udman","udman hotels   resorts","udmanhotels"]},
    {"name": "Azaya Beach Resort Goa", "ga4_id": "390141987", "domain": "azayabeachresortgoa.com", "keywords": ["azaya","azaya beach resort goa","azayabeachresortgoa","beach"]},
    {"name": "Hotel Rivatas by Ideal", "ga4_id": "386940786", "domain": "rivatas.com", "keywords": ["hotel rivatas by ideal","ideal","rivatas"]},
    {"name": "The Amayaa", "ga4_id": "386506157", "domain": "theamayaa.com", "keywords": ["amayaa","the amayaa","theamayaa"]},
    {"name": "MGM Hotels & Resorts", "ga4_id": "387093098", "domain": "mgm-hotels.com", "keywords": ["mgm","mgm hotels   resorts","mgm-hotels"]},
    {"name": "VOVAM SERVICED APARTMENT", "ga4_id": "387174049", "domain": "vovam.in", "keywords": ["apartment","serviced","vovam","vovam serviced apartment"]},
    {"name": "Suryavilas Luxury Resort and Spa", "ga4_id": "390263689", "domain": "suryavilas.com", "keywords": ["luxury","spa","suryavilas","suryavilas luxury resort and spa"]},
    {"name": "Nemesia", "ga4_id": "386499817", "domain": "nemesiahotels.com", "keywords": ["nemesia","nemesiahotels"]},
    {"name": "Ummed Hotels India", "ga4_id": "386496883", "domain": "ummedhotels.com", "keywords": ["india","ummed","ummed hotels india","ummedhotels"]},
    {"name": "Lime Tree Hotels & Service Apartment Private Limited", "ga4_id": "374794749", "domain": "limetreehotels.com", "keywords": ["apartment","lime","lime tree hotels   service apartment private limited","limetreehotels","service","tree"]},
    {"name": "La Marvella, Bengaluru", "ga4_id": "386940979", "domain": "lamarvella.com", "keywords": ["bengaluru","la marvella  bengaluru","lamarvella","marvella"]},
    {"name": "Tarika Hotels", "ga4_id": "391799931", "domain": "tarikahotels.com", "keywords": ["tarika","tarika hotels","tarikahotels"]},
    {"name": "The Atara Near Golf Course Road", "ga4_id": "386958279", "domain": "theatara.com", "keywords": ["atara","course","golf","near","the atara near golf course road","theatara"]},
    {"name": "Maya's Kings Kourt", "ga4_id": "397007515", "domain": "kingskourthotel.in", "keywords": ["kings","kingskourthotel","kourt","maya","maya s kings kourt"]},
    {"name": "Welcome Group of Hotel -Redirects", "ga4_id": "386913066", "domain": "welcomegroupofhotels.in", "keywords": ["welcome","welcome group of hotel  redirects","welcomegroupofhotels"]},
    {"name": "Hotel Hindusthan International, Kolkata", "ga4_id": "386522408", "domain": "hhikolkata.com", "keywords": ["hhikolkata","hindusthan","hotel hindusthan international  kolkata","international"]},
    {"name": "Fateh Collection", "ga4_id": "387248060", "domain": "fatehcollection.com", "keywords": ["collection","fateh","fateh collection","fatehcollection"]},
    {"name": "The Tattwaa Corbett Spa & Resort", "ga4_id": "391565789", "domain": "tattwaa.com", "keywords": ["corbett","spa","tattwaa","the tattwaa corbett spa   resort"]},
    {"name": "Kenilworth Hotels & Resorts", "ga4_id": "386873354", "domain": "kenilworthhotels.com", "keywords": ["kenilworth","kenilworth hotels   resorts","kenilworthhotels"]},
    {"name": "The Aanandam Hotel Resort", "ga4_id": "386635252", "domain": "theaanandam.in", "keywords": ["aanandam","the aanandam hotel resort","theaanandam"]},
    {"name": "The Residency Group of Hotels", "ga4_id": "386927028", "domain": "theresidency.com", "keywords": ["residency","the residency group of hotels","theresidency"]},
    {"name": "OAK by Signature Group", "ga4_id": "402602161", "domain": "oakbysignaturegroup.com", "keywords": ["oak","oak by signature group","oakbysignaturegroup","signature"]},
    {"name": "The Suryaa New Delhi", "ga4_id": "387012482", "domain": "thesuryaa.com", "keywords": ["new","suryaa","the suryaa new delhi","thesuryaa"]},
    {"name": "The Boma Hotels", "ga4_id": "386272229", "domain": "theboma.co.ke", "keywords": ["boma","the boma hotels","theboma"]},
    {"name": "The Littlearth Group", "ga4_id": "335459521", "domain": "littlearth.in", "keywords": ["littlearth","the littlearth group"]},
    {"name": "Aureum Palace Hotel & Resort, Bagan", "ga4_id": "402597295", "domain": "unknown", "keywords": ["aureum","aureum palace hotel   resort  bagan","bagan"]},
    {"name": "Cygnett Hotels", "ga4_id": "390396626", "domain": "cygnetthotels.com", "keywords": ["cygnett","cygnett hotels","cygnetthotels"]},
    {"name": "Hotel Hindusthan International Select, Bengaluru", "ga4_id": "386123576", "domain": "hhibangalore.com", "keywords": ["bengaluru","hhibangalore","hindusthan","hotel hindusthan international select  bengaluru","international","select"]},
    {"name": "Stone Wood Hotels & Resorts", "ga4_id": "387150024", "domain": "stonewoodresorts.com", "keywords": ["stone","stone wood hotels   resorts","stonewoodresorts","wood"]},
    {"name": "Mango Grove", "ga4_id": "387206382", "domain": "mangogrovehotel.com", "keywords": ["grove","mango","mango grove","mangogrovehotel"]},
    {"name": "The Raj VIlas", "ga4_id": "396978428", "domain": "therajvilas.com", "keywords": ["raj","the raj vilas","therajvilas","vilas"]},
    {"name": "Themis Mudhouse Resorts", "ga4_id": "386631414", "domain": "themismudhouse.com", "keywords": ["mudhouse","themis","themis mudhouse resorts","themismudhouse"]},
    {"name": "Elite by Signature", "ga4_id": "391539744", "domain": "elitebysignature.com", "keywords": ["elite","elite by signature","elitebysignature","signature"]},
    {"name": "Asian Suites", "ga4_id": "387089649", "domain": "asiansuites.in", "keywords": ["asian","asian suites","asiansuites"]},
    {"name": "Kings International Juhu", "ga4_id": "383676442", "domain": "kingsinternational.com", "keywords": ["international","juhu","kings","kings international juhu","kingsinternational"]},
    {"name": "SILVER LINE RETREAT", "ga4_id": "386842126", "domain": "slrhotels.com", "keywords": ["line","retreat","silver","silver line retreat","slrhotels"]},
    {"name": "Popa Mountain Resort", "ga4_id": "396722453", "domain": "unknown", "keywords": ["mountain","popa","popa mountain resort"]},
    {"name": "VRR  Astoria Hotel and Conventional Centre", "ga4_id": "386595795", "domain": "vrrhotels.com", "keywords": ["astoria","centre","conventional","vrr","vrr  astoria hotel and conventional centre","vrrhotels"]},
    {"name": "Rhythm Hospitality", "ga4_id": "299379837", "domain": "rhythmhospitality.com", "keywords": ["hospitality","rhythm","rhythm hospitality","rhythmhospitality"]},
    {"name": "The Sonnet", "ga4_id": "479853320", "domain": "thesonnet.com", "keywords": ["sonnet","the sonnet","thesonnet"]},
    {"name": "Aureum Palace Hotels & Resorts", "ga4_id": "386222825", "domain": "aureumpalacehotel.com", "keywords": ["aureum","aureum palace hotels   resorts","aureumpalacehotel"]},
    {"name": "Hotel Shiva Continental, Mussoorie", "ga4_id": "367916995", "domain": "shivacontinental.in", "keywords": ["continental","hotel shiva continental  mussoorie","mussoorie","shiva","shivacontinental"]},
    {"name": "Best Western, Vrindavan", "ga4_id": "386826278", "domain": "bestwesternvrindavan.com", "keywords": ["best","best western  vrindavan","bestwesternvrindavan","vrindavan","western"]},
    {"name": "Lagoon De Pondy Resort", "ga4_id": "386649566", "domain": "lagoonpondy.com", "keywords": ["lagoon","lagoon de pondy resort","lagoonpondy","pondy"]},
    {"name": "Asiatic Rooftop Bar and Restaurant", "ga4_id": "368352978", "domain": "theasiatic.com", "keywords": ["asiatic","asiatic rooftop bar and restaurant","bar","restaurant","rooftop","theasiatic"]},
    {"name": "Sigma International Group of Hotels", "ga4_id": "387265264", "domain": "sigmagroupofhotels.com", "keywords": ["international","sigma","sigma international group of hotels","sigmagroupofhotels"]},
    {"name": "La Classic Hotels", "ga4_id": "386179227", "domain": "laclassichotels.com", "keywords": ["classic","la classic hotels","laclassichotels"]},
    {"name": "The Residences at CSE", "ga4_id": "386306772", "domain": "theresidences.in", "keywords": ["cse","residences","the residences at cse","theresidences"]},
    {"name": "Bawa Group of Hotels", "ga4_id": "331318461", "domain": "bawahotels.com", "keywords": ["bawa","bawa group of hotels","bawahotels"]},
    {"name": "The Ivy Anjuna", "ga4_id": "387182624", "domain": "ivyanjuna.com", "keywords": ["anjuna","ivy","ivyanjuna","the ivy anjuna"]},
    {"name": "Hotel Bali Nova", "ga4_id": "383604541", "domain": "hotelbalinova.com", "keywords": ["bali","hotel bali nova","hotelbalinova","nova"]},
    {"name": "Evolve Back", "ga4_id": "337693858", "domain": "evolveback.com", "keywords": ["back","evolve","evolve back","evolveback"]},
    {"name": "Hotel Park Ocean", "ga4_id": "396724427", "domain": "hotelparkocean.com", "keywords": ["hotel park ocean","hotelparkocean","ocean","park"]},
    {"name": "Hotel The Grand Dragon Ladakh", "ga4_id": "386721420", "domain": "thegranddragonladakh.com", "keywords": ["dragon","hotel the grand dragon ladakh","ladakh","thegranddragonladakh"]},
    {"name": "Misty Blue", "ga4_id": "386669850", "domain": "mistybluehotel.com", "keywords": ["blue","misty","misty blue","mistybluehotel"]},
    {"name": "Earthaa Escapes", "ga4_id": "386755052", "domain": "earthaa.in", "keywords": ["earthaa","earthaa escapes","escapes"]},
    {"name": "Mahoora by Eco Team", "ga4_id": "386555767", "domain": "mahoora.lk", "keywords": ["eco","mahoora","mahoora by eco team","team"]},
    {"name": "Ahaspokuna Bush Walks Camp by Eco Team", "ga4_id": "371851598", "domain": "ahaspokuna.com", "keywords": ["ahaspokuna","ahaspokuna bush walks camp by eco team","bush","camp","walks"]},
    {"name": "Big Game by Eco Team", "ga4_id": "368881869", "domain": "srilankabiggamesafaris.com", "keywords": ["big","big game by eco team","eco","game","srilankabiggamesafaris","team"]},
    {"name": "Happy Stay_Demo", "ga4_id": "392120583", "domain": "happystay.com", "keywords": ["happy","happy stay_demo","happystay","stay_demo"]},
    {"name": "Dolphin Hotel Pvt. Ltd, Visakhapatnam, AP, India", "ga4_id": "392186474", "domain": "dolphinhotelsvizag.com", "keywords": ["dolphin","dolphin hotel pvt  ltd  visakhapatnam  ap  india","dolphinhotelsvizag","ltd","pvt","visakhapatnam"]},
    {"name": "Foxoso Group of Hotels", "ga4_id": "386498003", "domain": "foxosohotels.com", "keywords": ["foxoso","foxoso group of hotels","foxosohotels"]},
    {"name": "Clarion Bangalore", "ga4_id": "365557935", "domain": "clarionbangalore.com", "keywords": ["clarion","clarion bangalore","clarionbangalore"]},
    {"name": "Fort Dadhikar, Alwar", "ga4_id": "396725744", "domain": "dadhikar.in", "keywords": ["alwar","dadhikar","fort","fort dadhikar  alwar"]},
    {"name": "RELAX INN HOTEL & RESORT", "ga4_id": "387102267", "domain": "relaxinn.co.in", "keywords": ["relax","relax inn hotel   resort","relaxinn"]},
    {"name": "Dimora Hotels and Resorts", "ga4_id": "386654627", "domain": "thedimorahotels.com", "keywords": ["dimora","dimora hotels and resorts","thedimorahotels"]},
    {"name": "Rangamati Garden Resort", "ga4_id": "375525753", "domain": "rangamatigardenresort.in", "keywords": ["garden","rangamati","rangamati garden resort","rangamatigardenresort"]},
    {"name": "Liverpool Hotels", "ga4_id": "386792010", "domain": "theliverpoolhotels.com", "keywords": ["liverpool","liverpool hotels","theliverpoolhotels"]},
    {"name": "ROSASTAYS", "ga4_id": "320671192", "domain": "rosastays.com", "keywords": ["rosastays"]},
    {"name": "The Den Corbett Resort & Spa, Kumeria", "ga4_id": "386571735", "domain": "thedencorbett.in", "keywords": ["corbett","den","kumeria","spa","the den corbett resort   spa  kumeria","thedencorbett"]},
    {"name": "Magnus Hotels & Apartments LLP", "ga4_id": "386363539", "domain": "staymagnus.com", "keywords": ["apartments","llp","magnus","magnus hotels   apartments llp","staymagnus"]},
    {"name": "Surya Bagh - A Luxury Hideaway", "ga4_id": "366447737", "domain": "suryabagh.com", "keywords": ["bagh","hideaway","luxury","surya","surya bagh   a luxury hideaway","suryabagh"]},
    {"name": "Wedlock Greens Hotel & Resorts", "ga4_id": "386105057", "domain": "wedlockgreens.com", "keywords": ["greens","wedlock","wedlock greens hotel   resorts","wedlockgreens"]},
    {"name": "Adamo Hospitality LLP", "ga4_id": "386494253", "domain": "adamohotels.com", "keywords": ["adamo","adamo hospitality llp","adamohotels","hospitality","llp"]},
    {"name": "Rosetum Hotels", "ga4_id": "318625782", "domain": "rosetum.in", "keywords": ["rosetum","rosetum hotels"]},
    {"name": "Hotel Grand A View", "ga4_id": "386511060", "domain": "hotelgrandaview.com", "keywords": ["hotel grand a view","hotelgrandaview","view"]},
    {"name": "Home2 India", "ga4_id": "386822594", "domain": "home2india.com", "keywords": ["home2","home2 india","home2india","india"]},
    {"name": "The Allure Grand Resort – A Unit of Divine Hospitality", "ga4_id": "386201641", "domain": "alluregrandresorts.com", "keywords": ["allure","alluregrandresorts","divine","hospitality","the allure grand resort   a unit of divine hospitality"]},
    {"name": "La Maison Hotel, Doha", "ga4_id": "387602964", "domain": "lamaisondoha.com", "keywords": ["doha","la maison hotel  doha","lamaisondoha","maison"]},
    {"name": "Quill Residences", "ga4_id": "396644469", "domain": "quillhotels.com", "keywords": ["quill","quill residences","quillhotels","residences"]},
    {"name": "The Cliff Edge Coorg Hotel", "ga4_id": "386236580", "domain": "thecliffedgecoorg.com", "keywords": ["cliff","coorg","edge","the cliff edge coorg hotel","thecliffedgecoorg"]},
    {"name": "O by Tamara", "ga4_id": "347557284", "domain": "obytamara.com", "keywords": ["o by tamara","obytamara","tamara"]},
    {"name": "The Clarks  Varanasi", "ga4_id": "386771478", "domain": "clarkshotels.com", "keywords": ["clarks","clarkshotels","the clarks  varanasi","varanasi"]},
    {"name": "Hotel Deccan Serai Grande, Gachibowli, 4 Star", "ga4_id": "386839529", "domain": "deccanserai.com", "keywords": ["deccan","deccanserai","gachibowli","grande","hotel deccan serai grande  gachibowli  4 star","serai"]},
    {"name": "Deccan Serai", "ga4_id": "386839529", "domain": "deccanserai1.com", "keywords": ["deccan","deccan serai","deccanserai1","serai"]},
    {"name": "Ramanashree Hotels & Resorts", "ga4_id": "391788085", "domain": "ramanashree.com", "keywords": ["ramanashree","ramanashree hotels   resorts"]},
    {"name": "Hotel Regent Laguna", "ga4_id": "396673506", "domain": "regentlaguna.com", "keywords": ["hotel regent laguna","laguna","regent","regentlaguna"]},
    {"name": "The Blackbuck Lodge, Velavadar", "ga4_id": "400277595", "domain": "theblackbucklodge.in", "keywords": ["blackbuck","lodge","the blackbuck lodge  velavadar","theblackbucklodge","velavadar"]},
    {"name": "V FIVE HOTEL", "ga4_id": "386300064", "domain": "vfivehotel.com", "keywords": ["five","v five hotel","vfivehotel"]},
    {"name": "Green Meadows Resort", "ga4_id": "402576895", "domain": "greenmeadowsresort.com", "keywords": ["green","green meadows resort","greenmeadowsresort","meadows"]},
    {"name": "Aval International", "ga4_id": "396680744", "domain": "hotelavalinternational.com", "keywords": ["aval","aval international","hotelavalinternational","international"]},
    {"name": "Fragrant Nature Hotels & Resorts", "ga4_id": "400424534", "domain": "fragrantnature.com", "keywords": ["fragrant","fragrant nature hotels   resorts","fragrantnature","nature"]},
    {"name": "Quality Inn Rockwell Grand, Bangalore", "ga4_id": "392143882", "domain": "qualityinnrockwell.com", "keywords": ["quality","quality inn rockwell grand  bangalore","qualityinnrockwell","rockwell"]},
    {"name": "Lamrin Hotels and Resorts", "ga4_id": "366955823", "domain": "lamrinhotels.com", "keywords": ["lamrin","lamrin hotels and resorts","lamrinhotels"]},
    {"name": "Unseen Boutique Hotel, Assagao - Goa", "ga4_id": "508231267", "domain": "unseenboutiquehotel.com", "keywords": ["assagao","boutique","unseen","unseen boutique hotel  assagao   goa","unseenboutiquehotel"]},
    {"name": "The Soco Hotels", "ga4_id": "403194254", "domain": "thesocohotel.com", "keywords": ["soco","the soco hotels","thesocohotel"]},
    {"name": "Hycinth Hotels", "ga4_id": "386787438", "domain": "hycinthhotels.com", "keywords": ["hycinth","hycinth hotels","hycinthhotels"]},
    {"name": "Hotel Montana Vyoo, Namchi", "ga4_id": "370592448", "domain": "hotelmontanavyoo.in", "keywords": ["hotel montana vyoo  namchi","hotelmontanavyoo","montana","namchi","vyoo"]},
    {"name": "Hotel East Bourne", "ga4_id": "396632402", "domain": "eastbourneresorts.com", "keywords": ["bourne","east","eastbourneresorts","hotel east bourne"]},
    {"name": "Voyage Hotels & Resorts", "ga4_id": "386242521", "domain": "thevoyagehotels.com", "keywords": ["thevoyagehotels","voyage","voyage hotels   resorts"]},
    {"name": "Ravishing Retreat", "ga4_id": "527889788", "domain": "ravishingretreat.in", "keywords": ["ravishing","ravishing retreat","ravishingretreat","retreat"]},
    {"name": "Yuhi Hospitality", "ga4_id": "373830258", "domain": "yuhihospitality.com", "keywords": ["hospitality","yuhi","yuhi hospitality","yuhihospitality"]},
    {"name": "Surya Haveli, Amer Fort Jaipur", "ga4_id": "386995999", "domain": "suryahaveli.com", "keywords": ["amer","fort","haveli","surya","surya haveli  amer fort jaipur","suryahaveli"]},
    {"name": "Sonaar Haveli", "ga4_id": "383707365", "domain": "sonaarhaveli.com", "keywords": ["haveli","sonaar","sonaar haveli","sonaarhaveli"]},
    {"name": "DGV Resort by Treat, Silvassa", "ga4_id": "383641249", "domain": "dgvresort.com", "keywords": ["dgv","dgv resort by treat  silvassa","dgvresort","silvassa","treat"]},
    {"name": "Denissons Beach Resort", "ga4_id": "390907387", "domain": "gamyamretreat.com", "keywords": ["beach","denissons","denissons beach resort","gamyamretreat"]},
    {"name": "Fort House Hotel", "ga4_id": "400439102", "domain": "hotelforthouse.com", "keywords": ["fort","fort house hotel","hotelforthouse","house"]},
    {"name": "The Raintree, St. Mary's Road", "ga4_id": "383142331", "domain": "raintreehotels.com", "keywords": ["mary","raintree","raintreehotels","road","the raintree  st  mary s road"]},
    {"name": "Hylife Hotel & Conventions", "ga4_id": "402573578", "domain": "hylifehotelsandconventions.com", "keywords": ["conventions","hylife","hylife hotel   conventions","hylifehotelsandconventions"]},
    {"name": "The Safari Quest", "ga4_id": "288369356", "domain": "thesafariquest.com", "keywords": ["quest","safari","the safari quest","thesafariquest"]},
    {"name": "Seventh Wave", "ga4_id": "390280897", "domain": "seventhwave.in", "keywords": ["seventh","seventh wave","seventhwave","wave"]},
    {"name": "MAYFAIR Hotels & Resorts", "ga4_id": "323058594", "domain": "mayfairhotels.com", "keywords": ["mayfair","mayfair hotels   resorts","mayfairhotels"]},
    {"name": "Hotel Diplomat", "ga4_id": "387057322", "domain": "hoteldiplomatmumbai.com", "keywords": ["diplomat","hotel diplomat","hoteldiplomatmumbai"]},
    {"name": "Tree House Resort, Jaipur", "ga4_id": "396228923", "domain": "treehouseresort.in", "keywords": ["house","tree","tree house resort  jaipur","treehouseresort"]},
    {"name": "GIS Select", "ga4_id": "386971540", "domain": "gishotels.com", "keywords": ["gis","gis select","gishotels","select"]},
    {"name": "La Selva Resorts", "ga4_id": "386185786", "domain": "laselvaresorts.com", "keywords": ["la selva resorts","laselvaresorts","selva"]},
    {"name": "Monarch Hotels", "ga4_id": "386253121", "domain": "monarchhotels.in", "keywords": ["monarch","monarch hotels","monarchhotels"]},
    {"name": "Royal Lotus View Resotel, Bangalore", "ga4_id": "386709238", "domain": "royallotusviewresotel.in", "keywords": ["lotus","resotel","royal","royal lotus view resotel  bangalore","royallotusviewresotel","view"]},
    {"name": "Neer Ganga Resorts", "ga4_id": "352339514", "domain": "neergangaresorts.com", "keywords": ["ganga","neer","neer ganga resorts","neergangaresorts"]},
    {"name": "Evolve Back", "ga4_id": "337693858", "domain": "evolveback.com", "keywords": ["back","evolve","evolve back","evolveback"]},
    {"name": "V Dine", "ga4_id": "392146863", "domain": "vdineindia.com", "keywords": ["dine","v dine","vdineindia"]},
    {"name": "Clover Greens Golf Course Resort", "ga4_id": "399058153", "domain": "clovergreens.com", "keywords": ["clover","clover greens golf course resort","clovergreens","course","golf","greens"]},
    {"name": "Kosh", "ga4_id": "383731908", "domain": "kosh.in", "keywords": ["kosh"]},
    {"name": "Viceroy Group of Hotels", "ga4_id": "396493553", "domain": "viceroyhoteldrj.com", "keywords": ["viceroy","viceroy group of hotels","viceroyhoteldrj"]},
    {"name": "JR Stays", "ga4_id": "396725011", "domain": "jrstays.com", "keywords": ["jr stays","jrstays","stays"]},
    {"name": "KertelSuites, Kinshasa", "ga4_id": "463391212", "domain": "kertelsuites.com", "keywords": ["kertelsuites","kertelsuites  kinshasa","kinshasa"]},
    {"name": "Haut Monde Hotels", "ga4_id": "4031404228", "domain": "hautmondehotels.com", "keywords": ["haut","haut monde hotels","hautmondehotels","monde"]},
    {"name": "Qcent Hotels", "ga4_id": "406011394", "domain": "qcenthotels.com", "keywords": ["qcent","qcent hotels","qcenthotels"]},
    {"name": "Shanti Seaview Resort & Spa", "ga4_id": "394757883", "domain": "shantihotels.com", "keywords": ["seaview","shanti","shanti seaview resort   spa","shantihotels","spa"]},
    {"name": "Rahi Hotels & Resorts", "ga4_id": "403446674", "domain": "rahihotels.com", "keywords": ["rahi","rahi hotels   resorts","rahihotels"]},
    {"name": "Panchvati Hotels", "ga4_id": "396052712", "domain": "panchvatihotels.com", "keywords": ["panchvati","panchvati hotels","panchvatihotels"]},
    {"name": "Echor Mandara TreeVilla Dharamshala", "ga4_id": "390316324", "domain": "unknown", "keywords": ["dharamshala","echor","echor mandara treevilla dharamshala","mandara","treevilla"]},
    {"name": "Golak - Presidential Villa by Denissons", "ga4_id": "396992736", "domain": "golakbydenissons.com", "keywords": ["denissons","golak","golak   presidential villa by denissons","golakbydenissons","presidential","villa"]},
    {"name": "A M Suites, Secunderabad", "ga4_id": "401165624", "domain": "amsuites.in", "keywords": ["a m suites  secunderabad","amsuites","secunderabad"]},
    {"name": "Ibex Resorts", "ga4_id": "397563830", "domain": "ibexresorts.com", "keywords": ["ibex","ibex resorts","ibexresorts"]},
    {"name": "HM Hotel & Resort, Dibrugarh", "ga4_id": "386896660", "domain": "hmresortdibrugarh.com", "keywords": ["dibrugarh","hm hotel   resort  dibrugarh","hmresortdibrugarh"]},
    {"name": "Le ROI Hotels & Resorts- DO NOT USE", "ga4_id": "386227278", "domain": "leroihotels.com", "keywords": ["le roi hotels   resorts  do not use","leroihotels","roi"]},
    {"name": "Holistic Eco-Resort, Kannur", "ga4_id": "394564692", "domain": "holisticecoresort.com", "keywords": ["eco","holistic","holistic eco resort  kannur","holisticecoresort","kannur"]},
    {"name": "Maxxvalue Hotels", "ga4_id": "396333937", "domain": "maxxvaluehotels.com", "keywords": ["maxxvalue","maxxvalue hotels","maxxvaluehotels"]},
    {"name": "3102BCE- DO NOT USE", "ga4_id": "387184944", "domain": "3102bce.co", "keywords": ["3102bce","3102bce  do not use"]},
    {"name": "Keeth House", "ga4_id": "386701854", "domain": "keethhouse.in", "keywords": ["house","keeth","keeth house","keethhouse"]},
    {"name": "TIO (THE INDIAN ORIGIN) HOTELS & RESORTS", "ga4_id": "425113387", "domain": "tiohotels.com", "keywords": ["indian","origin","tio","tio  the indian origin  hotels   resorts","tiohotels"]},
    {"name": "The Sierra - By The Lake", "ga4_id": "371016578", "domain": "sierraudaipur.com", "keywords": ["lake","sierra","sierraudaipur","the sierra   by the lake"]},
    {"name": "Kayal Island Retreat", "ga4_id": "398842679", "domain": "kayalislandretreat.com", "keywords": ["island","kayal","kayal island retreat","kayalislandretreat","retreat"]},
    {"name": "Chunda Hotels", "ga4_id": "407190875", "domain": "chundahotels.com", "keywords": ["chunda","chunda hotels","chundahotels"]},
    {"name": "Shwe San Eain Hotel", "ga4_id": "391613969", "domain": "shwesaneainhotel.com", "keywords": ["eain","san","shwe","shwe san eain hotel","shwesaneainhotel"]},
    {"name": "Juna Mahal, Ranthambore", "ga4_id": "399310439", "domain": "junamahal.co.in", "keywords": ["juna","juna mahal  ranthambore","junamahal","mahal","ranthambore"]},
    {"name": "Azara Beach House Luxury Villa", "ga4_id": "460784262", "domain": "azarabeachhouse.com", "keywords": ["azara","azara beach house luxury villa","azarabeachhouse","beach","house","luxury"]},
    {"name": "Hotel 39, Jamaica", "ga4_id": "407222645", "domain": "simplotel7896.com", "keywords": ["hotel 39  jamaica","jamaica","simplotel7896"]},
    {"name": "TGI Hotels and Resorts- DO NOT USE", "ga4_id": "388052695", "domain": "tgihotels.com", "keywords": ["tgi","tgi hotels and resorts  do not use","tgihotels"]},
    {"name": "Shrigo Hotels", "ga4_id": "400837339", "domain": "shrigohotels.com", "keywords": ["shrigo","shrigo hotels","shrigohotels"]},
    {"name": "Southern Grand Kashi, Varanasi", "ga4_id": "368721042", "domain": "southerngrandkashi.com", "keywords": ["kashi","southern","southern grand kashi  varanasi","southerngrandkashi","varanasi"]},
    {"name": "Mango Hill Hotels", "ga4_id": "316811728", "domain": "mangohillhotels.com", "keywords": ["hill","mango","mango hill hotels","mangohillhotels"]},
    {"name": "Pai Group of Hotels - DO NOT USE", "ga4_id": "386435848", "domain": "paihotels.com", "keywords": ["pai","pai group of hotels   do not use","paihotels"]},
    {"name": "Ramada Resort by Wyndham Khao Lak", "ga4_id": "382890402", "domain": "ramadakhaolak.com", "keywords": ["khao","lak","ramada","ramada resort by wyndham khao lak","ramadakhaolak","wyndham"]},
    {"name": "Wabi - Sabi by Alamiko", "ga4_id": "409039045", "domain": "wabisabi-alamiko.com", "keywords": ["alamiko","sabi","wabi","wabi   sabi by alamiko","wabisabi-alamiko"]},
    {"name": "Five Elements Hotels", "ga4_id": "413437773", "domain": "fiveelementshotels.com", "keywords": ["elements","five","five elements hotels","fiveelementshotels"]},
    {"name": "Hotel Ram International, Pondicherry", "ga4_id": "403593667", "domain": "hotelraminternational.in", "keywords": ["hotel ram international  pondicherry","hotelraminternational","international","pondicherry","ram"]},
    {"name": "Jayaram Hotel, Pondicherry", "ga4_id": "403402474", "domain": "jayaramhotel.com", "keywords": ["jayaram","jayaram hotel  pondicherry","jayaramhotel","pondicherry"]},
    {"name": "The Tamarind Hotel, Goa", "ga4_id": "493688032", "domain": "thetamarind.com", "keywords": ["tamarind","the tamarind hotel  goa","thetamarind"]},
    {"name": "Casa Cottage - Heritage Hotel in Bangalore (DO NOT USE)", "ga4_id": "386137038", "domain": "casacottage.com", "keywords": ["casa","casa cottage   heritage hotel in bangalore  do not use","casacottage","cottage","heritage"]},
    {"name": "Altitude Group of Hotels & Resorts (DO NOT USE)", "ga4_id": "403214400", "domain": "altitudehotelsresorts.co.in", "keywords": ["altitude","altitude group of hotels   resorts  do not use","altitudehotelsresorts"]},
    {"name": "Remasailam Homestay", "ga4_id": "362932730", "domain": "remasailam.com", "keywords": ["homestay","remasailam","remasailam homestay"]},
    {"name": "Monk’s Nirvanaa Hotel and Resort by Pearls Hospitality", "ga4_id": "405703722", "domain": "monksnirvanaa.com", "keywords": ["hospitality","monk","monk s nirvanaa hotel and resort by pearls hospitality","monksnirvanaa","nirvanaa","pearls"]},
    {"name": "Rosewood Apartment Hotels", "ga4_id": "404725770", "domain": "rosewoodhospitality.com", "keywords": ["apartment","rosewood","rosewood apartment hotels","rosewoodhospitality"]},
    {"name": "Trees N Tigers", "ga4_id": "410330475", "domain": "treesntigers.com", "keywords": ["tigers","trees","trees n tigers","treesntigers"]},
    {"name": "Danta Killa Shekhawati - A Heritage Hotel", "ga4_id": "395968574", "domain": "dantafort.com", "keywords": ["danta","danta killa shekhawati   a heritage hotel","dantafort","heritage","killa","shekhawati"]},
    {"name": "Golden Blossom Imperial Resorts, Lucknow", "ga4_id": "427574656", "domain": "goldenblossomresorts.com", "keywords": ["blossom","golden","golden blossom imperial resorts  lucknow","goldenblossomresorts","imperial","lucknow"]},
    {"name": "Art Boutique Hotel, Hyderabad", "ga4_id": "448834774", "domain": "arthotel.co.in", "keywords": ["art","art boutique hotel  hyderabad","arthotel","boutique"]},
    {"name": "The Vivaan Hotel & Resorts, Karnal", "ga4_id": "372404084", "domain": "thevivaan.com", "keywords": ["karnal","the vivaan hotel   resorts  karnal","thevivaan","vivaan"]},
    {"name": "Hotel Clarks Shiraz, Agra", "ga4_id": "424285945", "domain": "hotelclarksshiraz.com", "keywords": ["agra","clarks","hotel clarks shiraz  agra","hotelclarksshiraz","shiraz"]},
    {"name": "Cosy Tours", "ga4_id": "398371248", "domain": "cosyb.com", "keywords": ["cosy","cosy tours","cosyb","tours"]},
    {"name": "MANVAR Resort & Desert Camp", "ga4_id": "409476339", "domain": "manvar.com", "keywords": ["camp","desert","manvar","manvar resort   desert camp"]},
    {"name": "Night Hotel Bangkok- DO NOT USE", "ga4_id": "395540853", "domain": "nighthotels.com", "keywords": ["bangkok","night","night hotel bangkok  do not use","nighthotels"]},
    {"name": "Hotel Athome", "ga4_id": "465860066", "domain": "athomehyd.com", "keywords": ["athome","athomehyd","hotel athome"]},
    {"name": "FRESH LIVING", "ga4_id": "434294715", "domain": "freshlivingrooms.in", "keywords": ["fresh","fresh living","freshlivingrooms","living"]},
    {"name": "Dev Shree, Deogarh", "ga4_id": "416357284", "domain": "devshreedeogarh.com", "keywords": ["deogarh","dev","dev shree  deogarh","devshreedeogarh","shree"]},
    {"name": "Park Elanza", "ga4_id": "433552770", "domain": "parkelanza.com", "keywords": ["elanza","park","park elanza","parkelanza"]},
    {"name": "Bamboo Saa Hotels & Resorts", "ga4_id": "287972673", "domain": "bamboosaa.com", "keywords": ["bamboo","bamboo saa hotels   resorts","bamboosaa","saa"]},
    {"name": "Hotel City Inn, Varanasi", "ga4_id": "528600938", "domain": "hotelcityinnvaranasi.com", "keywords": ["city","hotel city inn  varanasi","hotelcityinnvaranasi","varanasi"]},
    {"name": "Bamboo Saa Mulberry Resort, Pushkar", "ga4_id": "287972673", "domain": "unknown", "keywords": ["bamboo","bamboo saa mulberry resort  pushkar","mulberry","pushkar","saa"]},
    {"name": "Ensober Hotels", "ga4_id": "422950653", "domain": "vinsober.com", "keywords": ["ensober","ensober hotels","vinsober"]},
    {"name": "Starling River Resort, Dandeli", "ga4_id": "5422373073", "domain": "starlingriverresort.com", "keywords": ["dandeli","river","starling","starling river resort  dandeli","starlingriverresort"]},
    {"name": "Crescent Water Park, Indore", "ga4_id": "414896343", "domain": "crescentwaterparks.com", "keywords": ["crescent","crescent water park  indore","crescentwaterparks","indore","park","water"]},
    {"name": "Suryaa Villa - A Boutique Heritage Hotel", "ga4_id": "410325757", "domain": "suryaavilla.com", "keywords": ["boutique","heritage","suryaa","suryaa villa   a boutique heritage hotel","suryaavilla","villa"]},
    {"name": "The Travancore Heritage Beach Resort", "ga4_id": "420550969", "domain": "thetravancoreheritage.com", "keywords": ["beach","heritage","the travancore heritage beach resort","thetravancoreheritage","travancore"]},
    {"name": "Waxpol Hotels and Resorts", "ga4_id": "425832470", "domain": "waxpolhotels.com", "keywords": ["waxpol","waxpol hotels and resorts","waxpolhotels"]},
    {"name": "Leisure Hotels- DO NOT USE", "ga4_id": "388045009", "domain": "leisurehotels.co.in", "keywords": ["leisure","leisure hotels  do not use","leisurehotels"]},
    {"name": "Lake Valley Resort and Spa, Tirupati", "ga4_id": "406154690", "domain": "lakevalleyresort.in", "keywords": ["lake","lake valley resort and spa  tirupati","lakevalleyresort","spa","tirupati","valley"]},
    {"name": "Maurya Hotels", "ga4_id": "514470547", "domain": "moryahotel.com", "keywords": ["maurya","maurya hotels","moryahotel"]},
    {"name": "Sumer hotel", "ga4_id": "407821292", "domain": "sumerhotel.com", "keywords": ["sumer","sumer hotel","sumerhotel"]},
    {"name": "Altitude Group of Hotels & Resorts - BE Shell", "ga4_id": "403214400", "domain": "altitudehotelsresorts.com", "keywords": ["altitude","altitude group of hotels   resorts   be shell","altitudehotelsresorts","shell"]},
    {"name": "Bed Chambers", "ga4_id": "405421819", "domain": "bedchambers.in", "keywords": ["bed","bed chambers","bedchambers","chambers"]},
    {"name": "Barsana Boutique Hotel, Kolkata", "ga4_id": "432576251", "domain": "barsanahotelkolkata.com", "keywords": ["barsana","barsana boutique hotel  kolkata","barsanahotelkolkata","boutique"]},
    {"name": "Sumi Yashshree Hotels & Resorts", "ga4_id": "419727460", "domain": "sumiyashshreehotels.com", "keywords": ["sumi","sumi yashshree hotels   resorts","sumiyashshreehotels","yashshree"]},
    {"name": "A HOTEL BY GREWALZ", "ga4_id": "406790963", "domain": "grewalz.in", "keywords": ["a hotel by grewalz","grewalz"]},
    {"name": "The Pearl Hotel, Hassan", "ga4_id": "409927948", "domain": "pearlhotels.in", "keywords": ["hassan","pearl","pearlhotels","the pearl hotel  hassan"]},
    {"name": "Trishvam", "ga4_id": "411742492", "domain": "trishvam.com", "keywords": ["trishvam"]},
    {"name": "The Heritage Club Tripura Castle Hotel and Spa, Shillong", "ga4_id": "410392902", "domain": "tripuracastle.com", "keywords": ["castle","club","heritage","the heritage club tripura castle hotel and spa  shillong","tripura","tripuracastle"]},
    {"name": "Springs Hotel, Tirupati", "ga4_id": "426958756", "domain": "springshoteltirupati.com", "keywords": ["springs","springs hotel  tirupati","springshoteltirupati","tirupati"]},
    {"name": "NATUREFULL RESORTS LLP", "ga4_id": "414685885", "domain": "naturefullresort.com", "keywords": ["llp","naturefull","naturefull resorts llp","naturefullresort"]},
    {"name": "Serviette Hotels", "ga4_id": "368294041", "domain": "serviettehotels.com", "keywords": ["serviette","serviette hotels","serviettehotels"]},
    {"name": "Century Resorts", "ga4_id": "409000349", "domain": "centuryresortdandeli.in", "keywords": ["century","century resorts","centuryresortdandeli"]},
    {"name": "Ekaa Agra", "ga4_id": "422970258", "domain": "ekaahotels.com", "keywords": ["agra","ekaa","ekaa agra","ekaahotels"]},
    {"name": "IOSIS Spa & Wellness", "ga4_id": "291155964", "domain": "iosiswellness.com", "keywords": ["iosis","iosis spa   wellness","iosiswellness","spa","wellness"]},
    {"name": "De Tulip Hotel and Resort Collection", "ga4_id": "416473217", "domain": "detulip.in", "keywords": ["collection","de tulip hotel and resort collection","detulip","tulip"]},
    {"name": "Hotel Kanchan", "ga4_id": "408283239", "domain": "hotelkanchankatra.in", "keywords": ["hotel kanchan","hotelkanchankatra","kanchan"]},
    {"name": "Hotel Dhruv Palace", "ga4_id": "411718256", "domain": "dhruvpalace.com", "keywords": ["dhruv","dhruvpalace","hotel dhruv palace"]},
    {"name": "Tripli Hotels", "ga4_id": "408154068", "domain": "triplihotels.com", "keywords": ["tripli","tripli hotels","triplihotels"]},
    {"name": "The Dukes Retreat", "ga4_id": "465163927", "domain": "dukesretreat.com", "keywords": ["dukes","dukesretreat","retreat","the dukes retreat"]},
    {"name": "The Resort, Mumbai (K Raheja Corp Private Limited)", "ga4_id": "423266070", "domain": "theresortmumbai.com", "keywords": ["corp","limited","private","raheja","the resort  mumbai  k raheja corp private limited","theresortmumbai"]},
    {"name": "Manuscript - Jhilwara Haveli", "ga4_id": "423048866", "domain": "manuscripthotels.com", "keywords": ["haveli","jhilwara","manuscript","manuscript   jhilwara haveli","manuscripthotels"]},
    {"name": "Ramada by Wyndham Kapurthala", "ga4_id": "422455025", "domain": "ramadakapurthala.com", "keywords": ["kapurthala","ramada","ramada by wyndham kapurthala","ramadakapurthala","wyndham"]},
    {"name": "President Hotel", "ga4_id": "419988957", "domain": "presidenthoteldubai.com", "keywords": ["president","president hotel","presidenthoteldubai"]},
    {"name": "Max Hotels REDIRECTS", "ga4_id": "415525937", "domain": "dume.com", "keywords": ["dume","max","max hotels redirects"]},
    {"name": "Sun Park Hotels", "ga4_id": "429805015", "domain": "sunparkresorts.com", "keywords": ["park","sun","sun park hotels","sunparkresorts"]},
    {"name": "The Beatle Hotel, Powai", "ga4_id": "421892203", "domain": "beatlehotels.com", "keywords": ["beatle","beatlehotels","powai","the beatle hotel  powai"]},
    {"name": "The Boma Nairobi", "ga4_id": "386272229", "domain": "theboma.co.ke", "keywords": ["boma","nairobi","the boma nairobi","theboma"]},
    {"name": "Royal Comfort Regency", "ga4_id": "414837458", "domain": "royalcomfortregency.com", "keywords": ["comfort","regency","royal","royal comfort regency","royalcomfortregency"]},
    {"name": "THE FOG RESORT AND SPA MUNNAR", "ga4_id": "414357934", "domain": "thefogmunnar.com", "keywords": ["fog","munnar","spa","the fog resort and spa munnar","thefogmunnar"]},
    {"name": "Sangam Hotels", "ga4_id": "423978386", "domain": "sangamhotels.com", "keywords": ["sangam","sangam hotels","sangamhotels"]},
    {"name": "Capitol Village Resort, Madikeri", "ga4_id": "419078847", "domain": "capitolvillage.org", "keywords": ["capitol","capitol village resort  madikeri","capitolvillage","madikeri","village"]},
    {"name": "Triptam Hotel, Vrindavan", "ga4_id": "427041686", "domain": "triptamhotels.com", "keywords": ["triptam","triptam hotel  vrindavan","triptamhotels","vrindavan"]},
    {"name": "Fiori Hotel, Jaipur", "ga4_id": "443076652", "domain": "fiorihotels.com", "keywords": ["fiori","fiori hotel  jaipur","fiorihotels"]},
    {"name": "Eden Woods Resort & Spa", "ga4_id": "508401736", "domain": "edenwoods.in", "keywords": ["eden","eden woods resort   spa","edenwoods","spa","woods"]},
    {"name": "Marco Polo Hotel LLC", "ga4_id": "364788333", "domain": "themarcopolohotel.com", "keywords": ["llc","marco","marco polo hotel llc","polo","themarcopolohotel"]},
    {"name": "EllBee Hotels", "ga4_id": "414268345", "domain": "ellbeehotels.com", "keywords": ["ellbee","ellbee hotels","ellbeehotels"]},
    {"name": "Yellow Bell Hotels", "ga4_id": "505757504", "domain": "yellowbellshotels.com", "keywords": ["bell","yellow","yellow bell hotels","yellowbellshotels"]},
    {"name": "La Oasis by Meraden", "ga4_id": "413971081", "domain": "unknown", "keywords": ["la oasis by meraden","meraden","oasis"]},
    {"name": "Star City Hotels", "ga4_id": "414415945", "domain": "starcityhotel.com", "keywords": ["city","star","star city hotels","starcityhotel"]},
    {"name": "Saavaj Resort, Sasan Gir", "ga4_id": "416380203", "domain": "saavajresort.in", "keywords": ["gir","saavaj","saavaj resort  sasan gir","saavajresort","sasan"]},
    {"name": "OCEAN SPRAY", "ga4_id": "429576374", "domain": "oceanspray.in", "keywords": ["ocean","ocean spray","oceanspray","spray"]},
    {"name": "Machaan Lodges & Resorts", "ga4_id": "445856467", "domain": "machaan.com", "keywords": ["lodges","machaan","machaan lodges   resorts"]},
    {"name": "Hotel Sarang Palace - Boutique Stays & Candlelight Dining", "ga4_id": "386711987", "domain": "hotelsarangpalace.com", "keywords": ["boutique","candlelight","hotel sarang palace   boutique stays   candlelight dining","hotelsarangpalace","sarang","stays"]},
    {"name": "Hotel Castle Mandawa, Jhunjunu", "ga4_id": "431176739", "domain": "castlemandawa.com", "keywords": ["castle","castlemandawa","hotel castle mandawa  jhunjunu","jhunjunu","mandawa"]},
    {"name": "Mandawa Haveli, Jaipur", "ga4_id": "431179274", "domain": "mandawahaveli.com", "keywords": ["haveli","mandawa","mandawa haveli  jaipur","mandawahaveli"]},
    {"name": "Corbett Adventure Resort, Ramnagar", "ga4_id": "435801633", "domain": "corbettadventureresort.com", "keywords": ["adventure","corbett","corbett adventure resort  ramnagar","corbettadventureresort","ramnagar"]},
    {"name": "Saraca Hotels & Resorts", "ga4_id": "421349758", "domain": "saracahotels.com", "keywords": ["saraca","saraca hotels   resorts","saracahotels"]},
    {"name": "SK international INNN", "ga4_id": "429341759", "domain": "skinternationalinnn.com", "keywords": ["innn","international","sk international innn","skinternationalinnn"]},
    {"name": "Stars and Windsongs", "ga4_id": "437298669", "domain": "starsandwindsongs.com", "keywords": ["stars","stars and windsongs","starsandwindsongs","windsongs"]},
    {"name": "Lemonridge Hotels", "ga4_id": "428652286", "domain": "lemonridgehotels.com", "keywords": ["lemonridge","lemonridge hotels","lemonridgehotels"]},
    {"name": "ZENQ Hotels & Resorts", "ga4_id": "428295418", "domain": "zenqhotels.com", "keywords": ["zenq","zenq hotels   resorts","zenqhotels"]},
    {"name": "Wyt Hotels", "ga4_id": "415095216", "domain": "wythotels.com", "keywords": ["wyt","wyt hotels","wythotels"]},
    {"name": "The Claridges", "ga4_id": "419780812", "domain": "claridges-1.com", "keywords": ["claridges","claridges-1","the claridges"]},
    {"name": "Hotel Golden Orchard", "ga4_id": "419909103", "domain": "hotelgoldenorchard.com", "keywords": ["golden","hotel golden orchard","hotelgoldenorchard","orchard"]},
    {"name": "GRT Hotels & Resorts", "ga4_id": "464163304", "domain": "grthotels.com", "keywords": ["grt","grt hotels   resorts","grthotels"]},
    {"name": "Coral Reef Hotel & Resort- DNU", "ga4_id": "387142703", "domain": "coralreefandaman.com", "keywords": ["coral","coral reef hotel   resort  dnu","coralreefandaman","reef"]},
    {"name": "Best Western Plus Revanta Resort & Spa", "ga4_id": "421303271", "domain": "bestwesternplusrevanta.com", "keywords": ["best","best western plus revanta resort   spa","bestwesternplusrevanta","plus","revanta","western"]},
    {"name": "Neelambari Ecotourism", "ga4_id": "422715653", "domain": "neelambari.co.in", "keywords": ["ecotourism","neelambari","neelambari ecotourism"]},
    {"name": "Hotel Nexus", "ga4_id": "426547070", "domain": "hotelnexus.in", "keywords": ["hotel nexus","hotelnexus","nexus"]},
    {"name": "Fairway Colombo", "ga4_id": "333089809", "domain": "fairwaycolombo.com", "keywords": ["colombo","fairway","fairway colombo","fairwaycolombo"]},
    {"name": "Pagoda Centurion Mussoorie", "ga4_id": "393050332", "domain": "pagodacenturion.com", "keywords": ["centurion","mussoorie","pagoda","pagoda centurion mussoorie","pagodacenturion"]},
    {"name": "Mumbai House Hotels", "ga4_id": "429543025", "domain": "mumbaihousehotels.com", "keywords": ["house","mumbai house hotels","mumbaihousehotels"]},
    {"name": "Alibu Resort Nha Trang", "ga4_id": "411956342", "domain": "aliburesort.com", "keywords": ["alibu","alibu resort nha trang","aliburesort","nha","trang"]},
    {"name": "Kavya Himalayas", "ga4_id": "449308072", "domain": "kavyaresortandspa.com", "keywords": ["himalayas","kavya","kavya himalayas","kavyaresortandspa"]},
    {"name": "Ravishing Retreat - Day Outing", "ga4_id": "367539048", "domain": "ravishingretreat.in", "keywords": ["day","outing","ravishing","ravishing retreat   day outing","ravishingretreat","retreat"]},
    {"name": "Matsya Island Retreat by Island Quest", "ga4_id": "285262774", "domain": "matsyahavelock.com", "keywords": ["island","matsya","matsya island retreat by island quest","matsyahavelock","retreat"]},
    {"name": "MGM Dizzee World DNU", "ga4_id": "430509922", "domain": "mgmdizzeeworld-dnu.com", "keywords": ["dizzee","mgm","mgm dizzee world dnu","mgmdizzeeworld-dnu","world"]},
    {"name": "Kadkani River Resort, Coorg (DO NOT USE)", "ga4_id": "386195558", "domain": "kadkani.com", "keywords": ["coorg","kadkani","kadkani river resort  coorg  do not use","river"]},
    {"name": "Windermere Estate", "ga4_id": "439502978", "domain": "windermeremunnar.com", "keywords": ["estate","windermere","windermere estate","windermeremunnar"]},
    {"name": "Windermere River house", "ga4_id": "440695244", "domain": "windermerethattekad.com", "keywords": ["house","river","windermere","windermere river house","windermerethattekad"]},
    {"name": "Hotel Park By Signature Group", "ga4_id": "426909685", "domain": "hotelparkhyd.com", "keywords": ["hotel park by signature group","hotelparkhyd","park","signature"]},
    {"name": "Rainwood Hotels", "ga4_id": "426315667", "domain": "rainwoodhotels.com", "keywords": ["rainwood","rainwood hotels","rainwoodhotels"]},
    {"name": "Indian Heritage Hotels Association", "ga4_id": "462697737", "domain": "indianheritagehotels.com", "keywords": ["association","heritage","indian","indian heritage hotels association","indianheritagehotels"]},
    {"name": "Utsav Camp Sariska", "ga4_id": "453611763", "domain": "utsavcampsariska.com", "keywords": ["camp","sariska","utsav","utsav camp sariska","utsavcampsariska"]},
    {"name": "Saccharum Safari Lodge, Kanha Tiger Reserve", "ga4_id": "452609376", "domain": "saccharumsafari.com", "keywords": ["kanha","lodge","saccharum","saccharum safari lodge  kanha tiger reserve","saccharumsafari","safari"]},
    {"name": "Hotel Wonder Hills @ Har ki Pauri Road Haridwar", "ga4_id": "478773592", "domain": "wonderhillshotel.in", "keywords": ["har","hills","hotel wonder hills   har ki pauri road haridwar","pauri","wonder","wonderhillshotel"]},
    {"name": "SRM Hotel Pvt Ltd- DO NOT USE", "ga4_id": "386248003", "domain": "srmhotels.com", "keywords": ["ltd","pvt","srm","srm hotel pvt ltd  do not use","srmhotels"]},
    {"name": "Caravela Beach Resort Goa", "ga4_id": "391611760", "domain": "olddesigncaravelabeachresortgoa.com", "keywords": ["beach","caravela","caravela beach resort goa","olddesigncaravelabeachresortgoa"]},
    {"name": "Vythiri Resort, Wayanad", "ga4_id": "314960716", "domain": "vythiriresort.com", "keywords": ["vythiri","vythiri resort  wayanad","vythiriresort","wayanad"]},
    {"name": "Bengaluru Resort", "ga4_id": "357767337", "domain": "wonderla12.com", "keywords": ["bengaluru","bengaluru resort","wonderla12"]},
    {"name": "Kiranshree Grand Hotel", "ga4_id": "467379259", "domain": "kiranshreegrand.com", "keywords": ["kiranshree","kiranshree grand hotel","kiranshreegrand"]},
    {"name": "Visthara - Urban Boutique Hotel", "ga4_id": "430653590", "domain": "vistharahotel.com", "keywords": ["boutique","urban","visthara","visthara   urban boutique hotel","vistharahotel"]},
    {"name": "The Rudraksh A Himalayan Retreat", "ga4_id": "410475263", "domain": "therudrakshretreat.com", "keywords": ["himalayan","retreat","rudraksh","the rudraksh a himalayan retreat","therudrakshretreat"]},
    {"name": "Hotel Sannidhi Emerald", "ga4_id": "441419296", "domain": "sannidhiemerald.com", "keywords": ["emerald","hotel sannidhi emerald","sannidhi","sannidhiemerald"]},
    {"name": "Araiya Hotels & Resorts", "ga4_id": "429821260", "domain": "araiyahotels.com", "keywords": ["araiya","araiya hotels   resorts","araiyahotels"]},
    {"name": "Parent Nidhi", "ga4_id": "428669706", "domain": "nidhii.com", "keywords": ["nidhi","nidhii","parent","parent nidhi"]},
    {"name": "Hotel Jaswin", "ga4_id": "428653982", "domain": "hoteljaswin.com", "keywords": ["hotel jaswin","hoteljaswin","jaswin"]},
    {"name": "Greenleaf The Resort & Spa", "ga4_id": "411283075", "domain": "greenleaftheresort.com", "keywords": ["greenleaf","greenleaf the resort   spa","greenleaftheresort","spa"]},
    {"name": "Hotel Amit", "ga4_id": "338938662", "domain": "hotelamit.com", "keywords": ["amit","hotel amit","hotelamit"]},
    {"name": "Hotel Grand Visava", "ga4_id": "412852547", "domain": "hotelgrandvisava.com", "keywords": ["hotel grand visava","hotelgrandvisava","visava"]},
    {"name": "Hotel Rj", "ga4_id": "441446250", "domain": "hotelrj.in", "keywords": ["hotel rj","hotelrj"]},
    {"name": "Parakkat Nature Hotel and Resorts, Munnar", "ga4_id": "429574395", "domain": "parakkatresorts.com", "keywords": ["munnar","nature","parakkat","parakkat nature hotel and resorts  munnar","parakkatresorts"]},
    {"name": "Shervani Hotels", "ga4_id": "438514349", "domain": "shervanihotels.com", "keywords": ["shervani","shervani hotels","shervanihotels"]},
    {"name": "Mango Leaf Lake Resort, Pune", "ga4_id": "434137743", "domain": "mangoleafresorts.com", "keywords": ["lake","leaf","mango","mango leaf lake resort  pune","mangoleafresorts"]},
    {"name": "Flutter Hotels & Resorts, Lansdowne", "ga4_id": "453278656", "domain": "flutterhotel.com", "keywords": ["flutter","flutter hotels   resorts  lansdowne","flutterhotel","lansdowne"]},
    {"name": "Jardin Hotels", "ga4_id": "442464027", "domain": "jardinhotels.com", "keywords": ["jardin","jardin hotels","jardinhotels"]},
    {"name": "Khanvel Resort, Silvassa, Vandhara resorts pvt. Ltd", "ga4_id": "326506278", "domain": "khanvelresort.com", "keywords": ["khanvel","khanvel resort  silvassa  vandhara resorts pvt  ltd","khanvelresort","pvt","silvassa","vandhara"]},
    {"name": "Entartica seaWorld,  Raipur Chattisgarh", "ga4_id": "352552304", "domain": "unknown", "keywords": ["chattisgarh","entartica","entartica seaworld   raipur chattisgarh","raipur","seaworld"]},
    {"name": "Hotel Kanishka", "ga4_id": "441416982", "domain": "hotelkanishkamanali.com", "keywords": ["hotel kanishka","hotelkanishkamanali","kanishka"]},
    {"name": "The Manora Woods Resort", "ga4_id": "409625756", "domain": "themanorawoodsresort.com", "keywords": ["manora","the manora woods resort","themanorawoodsresort","woods"]},
    {"name": "CGH Earth", "ga4_id": "309715901", "domain": "cghearth.com", "keywords": ["cgh","cgh earth","cghearth","earth"]},
    {"name": "MANVÂR Resort & Desert Camp", "ga4_id": "409476339", "domain": "manvar.com", "keywords": ["camp","desert","manvar","manvâr","manvâr resort   desert camp"]},
    {"name": "Memoire Siem Reap Hotel", "ga4_id": "434484491", "domain": "memoiresiemreaphotel.com", "keywords": ["memoire","memoire siem reap hotel","memoiresiemreaphotel","reap","siem"]},
    {"name": "Entartica seaworld", "ga4_id": "352552304", "domain": "entartica.com", "keywords": ["entartica","entartica seaworld","seaworld"]},
    {"name": "Entartica seaworld", "ga4_id": "352552304", "domain": "entartica.com", "keywords": ["entartica","entartica seaworld","seaworld"]},
    {"name": "The Isabelle", "ga4_id": "448941894", "domain": "theisabellenaga.com", "keywords": ["isabelle","the isabelle","theisabellenaga"]},
    {"name": "MGM Dizzee World", "ga4_id": "430509922", "domain": "mgmdizzeeworld.com", "keywords": ["dizzee","mgm","mgm dizzee world","mgmdizzeeworld","world"]},
    {"name": "The Manor House, Dehradun", "ga4_id": "440389354", "domain": "themanorhousehotels.com", "keywords": ["dehradun","house","manor","the manor house  dehradun","themanorhousehotels"]},
    {"name": "Summit Hotels & Resorts", "ga4_id": "390937652", "domain": "summithotels.in", "keywords": ["summit","summit hotels   resorts","summithotels"]},
    {"name": "mesta Hotel", "ga4_id": "444062780", "domain": "mestahotel.com", "keywords": ["mesta","mesta hotel","mestahotel"]},
    {"name": "The Silver Sky Hotels and Resorts, Chikkamagaluru", "ga4_id": "437729614", "domain": "thesilversky.in", "keywords": ["chikkamagaluru","silver","sky","the silver sky hotels and resorts  chikkamagaluru","thesilversky"]},
    {"name": "Nirvana Luxury Hotel, Ludhiana", "ga4_id": "442263194", "domain": "nirvanahotels.co.in", "keywords": ["ludhiana","luxury","nirvana","nirvana luxury hotel  ludhiana","nirvanahotels"]},
    {"name": "Hotel Fortune Hyderabad Airport Zone", "ga4_id": "438001271", "domain": "fortuneairport.com", "keywords": ["airport","fortune","fortuneairport","hotel fortune hyderabad airport zone","zone"]},
    {"name": "Tulin Heritage Bungalow", "ga4_id": "443116103", "domain": "tulinbungalow.com", "keywords": ["bungalow","heritage","tulin","tulin heritage bungalow","tulinbungalow"]},
    {"name": "The Manor Sports & Wellness Hotel", "ga4_id": "449157687", "domain": "themanorhotel.in", "keywords": ["manor","sports","the manor sports   wellness hotel","themanorhotel","wellness"]},
    {"name": "The Manor Luxury Hotel, Shimla 1713846034", "ga4_id": "386685208", "domain": "unknown", "keywords": ["1713846034","luxury","manor","shimla","the manor luxury hotel  shimla 1713846034"]},
    {"name": "Peninsula Grand Hotel", "ga4_id": "448197107", "domain": "peninsulagrand.com", "keywords": ["peninsula","peninsula grand hotel","peninsulagrand"]},
    {"name": "Diamond Parks, Pune", "ga4_id": "461826912", "domain": "diamondparks.com", "keywords": ["diamond","diamond parks  pune","diamondparks","parks"]},
    {"name": "Faraway Cottages, Auli", "ga4_id": "450669295", "domain": "farawaycottages.com", "keywords": ["auli","cottages","faraway","faraway cottages  auli","farawaycottages"]},
    {"name": "Downtown Hostels - Anjuna", "ga4_id": "443121495", "domain": "8998_simplotel.com", "keywords": ["8998_simplotel","anjuna","downtown","downtown hostels   anjuna","hostels"]},
    {"name": "Saavaj Resort, Sasan Gir- DO NOT USE", "ga4_id": "416380203", "domain": "saavajresort.in", "keywords": ["gir","saavaj","saavaj resort  sasan gir  do not use","saavajresort","sasan"]},
    {"name": "Essentia Hotels & Resorts", "ga4_id": "440183733", "domain": "essentiahotels.in", "keywords": ["essentia","essentia hotels   resorts","essentiahotels"]},
    {"name": "Ecotel Hotels REDIRECTS (DNU)", "ga4_id": "440474754", "domain": "ecotelhotels.in", "keywords": ["ecotel","ecotel hotels redirects  dnu","ecotelhotels"]},
    {"name": "The Samai", "ga4_id": "441362182", "domain": "thesamai.com", "keywords": ["samai","the samai","thesamai"]},
    {"name": "Vagator Downtown, Goa", "ga4_id": "440134952", "domain": "vagatordowntown.com", "keywords": ["downtown","vagator","vagator downtown  goa","vagatordowntown"]},
    {"name": "The Grand Imperial", "ga4_id": "360673585", "domain": "hotelgrandimperial.com", "keywords": ["hotelgrandimperial","imperial","the grand imperial"]},
    {"name": "Hotel Grand Serene, Mysore", "ga4_id": "442330312", "domain": "hotelgrandserene.com", "keywords": ["hotel grand serene  mysore","hotelgrandserene","mysore","serene"]},
    {"name": "Tranquil Nest", "ga4_id": "441511602", "domain": "tranquilnests.com", "keywords": ["nest","tranquil","tranquil nest","tranquilnests"]},
    {"name": "Presidency Airport Hotel", "ga4_id": "441023607", "domain": "presidencyairporthotel.com", "keywords": ["airport","presidency","presidency airport hotel","presidencyairporthotel"]},
    {"name": "Mongas Hotel & Resort, Dalhousie", "ga4_id": "467420079", "domain": "hotelmongas.com", "keywords": ["dalhousie","hotelmongas","mongas","mongas hotel   resort  dalhousie"]},
    {"name": "Edwin Hospitality Services", "ga4_id": "447395848", "domain": "edwinhospitalityservices.com", "keywords": ["edwin","edwin hospitality services","edwinhospitalityservices","hospitality","services"]},
    {"name": "The Zion, Shimla", "ga4_id": "304570393", "domain": "thezionhotel.com", "keywords": ["shimla","the zion  shimla","thezionhotel","zion"]},
    {"name": "Dunagiri Retreat", "ga4_id": "440685105", "domain": "dunagiri.com", "keywords": ["dunagiri","dunagiri retreat","retreat"]},
    {"name": "The South Square Hotel, Bengaluru", "ga4_id": "453258058", "domain": "thesouthsquare.com", "keywords": ["bengaluru","south","square","the south square hotel  bengaluru","thesouthsquare"]},
    {"name": "Summer House, Nandi Hills", "ga4_id": "445362251", "domain": "nandisummerhouse.in", "keywords": ["hills","house","nandi","nandisummerhouse","summer","summer house  nandi hills"]},
    {"name": "The OnTime Hotel, Bangalore", "ga4_id": "448463316", "domain": "theontimehotel.com", "keywords": ["ontime","the ontime hotel  bangalore","theontimehotel"]},
    {"name": "Vistar Resorts and Hotels", "ga4_id": "446966067", "domain": "vistarresorts.in", "keywords": ["vistar","vistar resorts and hotels","vistarresorts"]},
    {"name": "KURJA Jawai", "ga4_id": "444559619", "domain": "kurjajawai.com", "keywords": ["jawai","kurja","kurja jawai","kurjajawai"]},
    {"name": "Bookmark Resorts", "ga4_id": "446884448", "domain": "bookmarkresorts.com", "keywords": ["bookmark","bookmark resorts","bookmarkresorts"]},
    {"name": "Atithi House", "ga4_id": "447443028", "domain": "atithihouse.com", "keywords": ["atithi","atithi house","atithihouse","house"]},
    {"name": "Sol Glow Resort, Nainital", "ga4_id": "457218955", "domain": "solglowhotels.com", "keywords": ["glow","nainital","sol","sol glow resort  nainital","solglowhotels"]},
    {"name": "Bergamont Hotels", "ga4_id": "455968737", "domain": "bergamonthotels.com", "keywords": ["bergamont","bergamont hotels","bergamonthotels"]},
    {"name": "Hotel Prime Classic", "ga4_id": "444589726", "domain": "comforthometel.in", "keywords": ["classic","comforthometel","hotel prime classic","prime"]},
    {"name": "Royale Assagao", "ga4_id": "448575576", "domain": "royaleassagao.com", "keywords": ["assagao","royale","royale assagao","royaleassagao"]},
    {"name": "Swosti Group", "ga4_id": "324675095", "domain": "swostihotels.com", "keywords": ["swosti","swosti group","swostihotels"]},
    {"name": "Sathyam Grand Resort", "ga4_id": "445626286", "domain": "sathyamgrouphotels.in", "keywords": ["sathyam","sathyam grand resort","sathyamgrouphotels"]},
    {"name": "Sathyam Grand Resort - DNU", "ga4_id": "386107648", "domain": "sathyamgrouphotels-dnu1.in", "keywords": ["sathyam","sathyam grand resort   dnu","sathyamgrouphotels-dnu1"]},
    {"name": "Fragrant Nature Hotels- DO NOT USE", "ga4_id": "400424534", "domain": "fragrantnature.com", "keywords": ["fragrant","fragrant nature hotels  do not use","fragrantnature","nature"]},
    {"name": "Club Charholi, Pune", "ga4_id": "448022430", "domain": "clubcharholi.com", "keywords": ["charholi","club","club charholi  pune","clubcharholi"]},
    {"name": "Opo Hotels", "ga4_id": "443767178", "domain": "opohotels.in", "keywords": ["opo","opo hotels","opohotels"]},
    {"name": "Hotel Lake View", "ga4_id": "443559439", "domain": "hotellakeviewchd.in", "keywords": ["hotel lake view","hotellakeviewchd","lake","view"]},
    {"name": "The Cindrella Hotel, Siliguri", "ga4_id": "446265143", "domain": "cindrellahotels.com", "keywords": ["cindrella","cindrellahotels","siliguri","the cindrella hotel  siliguri"]},
    {"name": "Claridges Collection", "ga4_id": "419780812", "domain": "claridges.com", "keywords": ["claridges","claridges collection","collection"]},
    {"name": "Grand Palace, Yercaud", "ga4_id": "466985469", "domain": "grandpalaceyercaud.com", "keywords": ["grand palace  yercaud","grandpalaceyercaud","yercaud"]},
    {"name": "Avana Resort", "ga4_id": "453849715", "domain": "avanaresort.in", "keywords": ["avana","avana resort","avanaresort"]},
    {"name": "Fragrant Nature Kollam", "ga4_id": "400424534", "domain": "fragrantnature.com", "keywords": ["fragrant","fragrant nature kollam","fragrantnature","kollam","nature"]},
    {"name": "Kamats India", "ga4_id": "454141729", "domain": "kamatsindia.com", "keywords": ["india","kamats","kamats india","kamatsindia"]},
    {"name": "Yogvan Holiday Apartments", "ga4_id": "448047246", "domain": "yogvanholidays.com", "keywords": ["apartments","holiday","yogvan","yogvan holiday apartments","yogvanholidays"]},
    {"name": "Lindsay Manor", "ga4_id": "444092794", "domain": "unknown", "keywords": ["lindsay","lindsay manor","manor"]},
    {"name": "Serenite Collection", "ga4_id": "470635492", "domain": "theserenite.com", "keywords": ["collection","serenite","serenite collection","theserenite"]},
    {"name": "Starlit Suites", "ga4_id": "448494744", "domain": "starlitsuites.com", "keywords": ["starlit","starlit suites","starlitsuites"]},
    {"name": "Hotel Bodhi Retreat By Basotel By Basotel", "ga4_id": "445476002", "domain": "hotelbodhiretreatrajgir.com", "keywords": ["basotel","bodhi","hotel bodhi retreat by basotel by basotel","hotelbodhiretreatrajgir","retreat"]},
    {"name": "Copper Leaf Hotels", "ga4_id": "448446476", "domain": "copperleafhotels.com", "keywords": ["copper","copper leaf hotels","copperleafhotels","leaf"]},
    {"name": "Camel Valley Resort & Spa, Igatpuri", "ga4_id": "464559620", "domain": "camelvalleyresort.com", "keywords": ["camel","camel valley resort   spa  igatpuri","camelvalleyresort","igatpuri","spa","valley"]},
    {"name": "Cedar Inn, Darjeeling", "ga4_id": "446285214", "domain": "cedarinn.in", "keywords": ["cedar","cedar inn  darjeeling","cedarinn","darjeeling"]},
    {"name": "Hotel La Premier", "ga4_id": "449659203", "domain": "hotellapremier.in", "keywords": ["hotel la premier","hotellapremier","premier"]},
    {"name": "Inde Hotels & Resorts", "ga4_id": "447631409", "domain": "indehotel.com", "keywords": ["inde","inde hotels   resorts","indehotel"]},
    {"name": "Greenfields Recreation And Convention Center Private Limited", "ga4_id": "465863233", "domain": "greenfieldsresort.in", "keywords": ["center","convention","greenfields","greenfields recreation and convention center private limited","greenfieldsresort","recreation"]},
    {"name": "Trance Hotels & Resorts", "ga4_id": "458197880", "domain": "trancehotels.com", "keywords": ["trance","trance hotels   resorts","trancehotels"]},
    {"name": "Hotel Aadithya, Chennai", "ga4_id": "491240832", "domain": "hotelaadithya.com", "keywords": ["aadithya","hotel aadithya  chennai","hotelaadithya"]},
    {"name": "Khairi Resort", "ga4_id": "445253871", "domain": "similipalkhairiresort.com", "keywords": ["khairi","khairi resort","similipalkhairiresort"]},
    {"name": "Lakeside Cottages", "ga4_id": "445367596", "domain": "lakesidecottages.lk", "keywords": ["cottages","lakeside","lakeside cottages","lakesidecottages"]},
    {"name": "Avianna Group of Hotels & Resorts", "ga4_id": "450817363", "domain": "aviannagroup.com", "keywords": ["avianna","avianna group of hotels   resorts","aviannagroup"]},
    {"name": "Sumi Stays, Bijanbari REDIRECTS (DNU)", "ga4_id": "449002552", "domain": "sumistays.in", "keywords": ["bijanbari","stays","sumi","sumi stays  bijanbari redirects  dnu","sumistays"]},
    {"name": "SSK Solitaire Hotel and Banquets", "ga4_id": "450652636", "domain": "thessksolitaire.com", "keywords": ["banquets","solitaire","ssk","ssk solitaire hotel and banquets","thessksolitaire"]},
    {"name": "YAAN Udaipur", "ga4_id": "409653805", "domain": "yaanudaipur.com", "keywords": ["udaipur","yaan","yaan udaipur","yaanudaipur"]},
    {"name": "Tea County Hotels", "ga4_id": "450808908", "domain": "teacorphotels.com", "keywords": ["county","tea","tea county hotels","teacorphotels"]},
    {"name": "Funky Leopard Safari Lodge", "ga4_id": "448965379", "domain": "yalaparksrilanka.com", "keywords": ["funky","funky leopard safari lodge","leopard","lodge","safari","yalaparksrilanka"]},
    {"name": "Tathastu Resorts", "ga4_id": "451344390", "domain": "tathasturesorts.com", "keywords": ["tathastu","tathastu resorts","tathasturesorts"]},
    {"name": "Hoysala Village Resort", "ga4_id": "456751666", "domain": "hoysalavillageresorts.com", "keywords": ["hoysala","hoysala village resort","hoysalavillageresorts","village"]},
    {"name": "Hotel Green Apple", "ga4_id": "458275459", "domain": "hotelgreenapple.co.in", "keywords": ["apple","green","hotel green apple","hotelgreenapple"]},
    {"name": "Hotel Aerotel, Hyderabad - A Unit of Comfort Hometel", "ga4_id": "457283642", "domain": "hotelaerotel.com", "keywords": ["aerotel","comfort","hometel","hotel aerotel  hyderabad   a unit of comfort hometel","hotelaerotel"]},
    {"name": "Three Hills Resort, Coorg", "ga4_id": "264026343", "domain": "3hills.in", "keywords": ["3hills","coorg","hills","three","three hills resort  coorg"]},
    {"name": "Coffeeberry Hills Chikmagalur", "ga4_id": "340694660", "domain": "coffeeberryhills.in", "keywords": ["chikmagalur","coffeeberry","coffeeberry hills chikmagalur","coffeeberryhills","hills"]},
    {"name": "The Oriental Residency", "ga4_id": "456741278", "domain": "theorientalresidency.com", "keywords": ["oriental","residency","the oriental residency","theorientalresidency"]},
    {"name": "Origin Boutique Hotel Goa", "ga4_id": "452523045", "domain": "originboutiquehotelgoa.com", "keywords": ["boutique","origin","origin boutique hotel goa","originboutiquehotelgoa"]},
    {"name": "Hotel Raai, Hosur", "ga4_id": "450325497", "domain": "hotelraai.com", "keywords": ["hosur","hotel raai  hosur","hotelraai","raai"]},
    {"name": "Sumitel Hotels REDIRECTS (DNU)", "ga4_id": "453670062", "domain": "sumitelhotels.in", "keywords": ["sumitel","sumitel hotels redirects  dnu","sumitelhotels"]},
    {"name": "Asapian Hotels", "ga4_id": "511173296", "domain": "asapianhotels.com", "keywords": ["asapian","asapian hotels","asapianhotels"]},
    {"name": "Staro Hotel - Hotel In Vijayawada", "ga4_id": "451098792", "domain": "starohotel.com", "keywords": ["staro","staro hotel   hotel in vijayawada","starohotel","vijayawada"]},
    {"name": "Vinayaga Hotels", "ga4_id": "461766007", "domain": "vinayagahotel.com", "keywords": ["vinayaga","vinayaga hotels","vinayagahotel"]},
    {"name": "Wonder Country Club and Resort, Kharagpur", "ga4_id": "453600841", "domain": "wondercountryclubandresort.com", "keywords": ["club","country","kharagpur","wonder","wonder country club and resort  kharagpur","wondercountryclubandresort"]},
    {"name": "Hotel Paris", "ga4_id": "450669898", "domain": "hotelparas.in", "keywords": ["hotel paris","hotelparas","paris"]},
    {"name": "Hotel Shaurya", "ga4_id": "450789193", "domain": "hotelshaurya.com", "keywords": ["hotel shaurya","hotelshaurya","shaurya"]},
    {"name": "AJ GRAND ELITE HOTEL", "ga4_id": "451559590", "domain": "ajgrandelite.com", "keywords": ["aj grand elite hotel","ajgrandelite","elite"]},
    {"name": "The Nanee, Bhaktapur, Nepal", "ga4_id": "460533733", "domain": "thenanee.com", "keywords": ["bhaktapur","nanee","nepal","the nanee  bhaktapur  nepal","thenanee"]},
    {"name": "Habba Dates Villa, Hampasandra", "ga4_id": "459071164", "domain": "9392habbadatesvilla.com", "keywords": ["9392habbadatesvilla","dates","habba","habba dates villa  hampasandra","hampasandra","villa"]},
    {"name": "Peerless Hotels & Resorts", "ga4_id": "459386421", "domain": "peerlesshotels.com", "keywords": ["peerless","peerless hotels   resorts","peerlesshotels"]},
    {"name": "The Lyca Resorts", "ga4_id": "451740809", "domain": "thelyca.com", "keywords": ["lyca","the lyca resorts","thelyca"]},
    {"name": "Beverly Hotel, Chennai", "ga4_id": "462690070", "domain": "beverlyhotels.com", "keywords": ["beverly","beverly hotel  chennai","beverlyhotels"]},
    {"name": "KETTI HEIGHTS RESORTS", "ga4_id": "459953577", "domain": "kettiheights.com", "keywords": ["heights","ketti","ketti heights resorts","kettiheights"]},
    {"name": "The Grand Cliff Resort", "ga4_id": "453670516", "domain": "thegrandcliff.com", "keywords": ["cliff","the grand cliff resort","thegrandcliff"]},
    {"name": "Palace Court Mediterranean Cuisine", "ga4_id": "456575477", "domain": "palacecourtrestaurant.com", "keywords": ["court","cuisine","mediterranean","palace court mediterranean cuisine","palacecourtrestaurant"]},
    {"name": "Clay Inn Hotels", "ga4_id": "376261887", "domain": "clayinnhotel.com", "keywords": ["clay","clay inn hotels","clayinnhotel"]},
    {"name": "The Sylvan Retreat, Dehradun", "ga4_id": "468549738", "domain": "thesylvanretreat.com", "keywords": ["dehradun","retreat","sylvan","the sylvan retreat  dehradun","thesylvanretreat"]},
    {"name": "Coffee Bean Resort", "ga4_id": "453318446", "domain": "coorgcoffeebeanresort.com", "keywords": ["bean","coffee","coffee bean resort","coorgcoffeebeanresort"]},
    {"name": "Avenue Hotels & Resorts", "ga4_id": "510238460", "domain": "timestopshere.in", "keywords": ["avenue","avenue hotels   resorts","timestopshere"]},
    {"name": "Rainforest", "ga4_id": "453429304", "domain": "rainforest.in", "keywords": ["rainforest"]},
    {"name": "Shalimar redirects (shalimarhotels.net)", "ga4_id": "386591553", "domain": "shalimarhotels.net", "keywords": ["net","shalimar","shalimar redirects  shalimarhotels net","shalimarhotels"]},
    {"name": "Crescent Spa & Resort, Indore", "ga4_id": "440389354", "domain": "unknown", "keywords": ["crescent","crescent spa   resort  indore","indore","spa"]},
    {"name": "Crescent Resorts", "ga4_id": "503784150", "domain": "crescentresorts.in", "keywords": ["crescent","crescent resorts","crescentresorts"]},
    {"name": "Luxor Park", "ga4_id": "454039445", "domain": "luxorhotels.in", "keywords": ["luxor","luxor park","luxorhotels","park"]},
    {"name": "The Canadian Woods Resort", "ga4_id": "454063365", "domain": "themount.in", "keywords": ["canadian","the canadian woods resort","themount","woods"]},
    {"name": "Aranya Vilas DNU", "ga4_id": "444559619", "domain": "9485_simplotel.com", "keywords": ["9485_simplotel","aranya","aranya vilas dnu","vilas"]},
    {"name": "Hotel Rajdarshan", "ga4_id": "459953981", "domain": "hotelrajdarshan.com", "keywords": ["hotel rajdarshan","hotelrajdarshan","rajdarshan"]},
    {"name": "Aranya Vilas by Mertia Hospitality", "ga4_id": "464881917", "domain": "mertiahospitality.com", "keywords": ["aranya","aranya vilas by mertia hospitality","hospitality","mertia","mertiahospitality","vilas"]},
    {"name": "Cross Roads Inn", "ga4_id": "464499466", "domain": "crossroadsinn.in", "keywords": ["cross","cross roads inn","crossroadsinn","roads"]},
    {"name": "TISSA’S INN", "ga4_id": "456770435", "domain": "tissasinn.in", "keywords": ["tissa","tissa s inn","tissasinn"]},
    {"name": "Darza Resorts", "ga4_id": "472460360", "domain": "darzaresorts.com", "keywords": ["darza","darza resorts","darzaresorts"]},
    {"name": "Hotel Apricia", "ga4_id": "456640414", "domain": "hotelapricia.com", "keywords": ["apricia","hotel apricia","hotelapricia"]},
    {"name": "Kurja Jawai - 1724842065-Dummy content(DNU)", "ga4_id": "444559619", "domain": "9518_simplotel.com", "keywords": ["1724842065","9518_simplotel","dummy","jawai","kurja","kurja jawai   1724842065 dummy content dnu"]},
    {"name": "City Centre Residency Bangalore", "ga4_id": "465146502", "domain": "ccrhotels.in", "keywords": ["ccrhotels","centre","city","city centre residency bangalore","residency"]},
    {"name": "Vrinda Hotels", "ga4_id": "464913759", "domain": "hotelvrinda.com", "keywords": ["hotelvrinda","vrinda","vrinda hotels"]},
    {"name": "Brij Castle", "ga4_id": "482792190", "domain": "brijcastle.com", "keywords": ["brij","brij castle","brijcastle","castle"]},
    {"name": "Hotel Seven", "ga4_id": "457307701", "domain": "hotelseven.in", "keywords": ["hotel seven","hotelseven","seven"]},
    {"name": "Hotel Aradhya Inn", "ga4_id": "457343765", "domain": "hotelaradhyainn.com", "keywords": ["aradhya","hotel aradhya inn","hotelaradhyainn"]},
    {"name": "Hotel Aurelia Comforts", "ga4_id": "457430101", "domain": "aureliacomforts.com", "keywords": ["aurelia","aureliacomforts","comforts","hotel aurelia comforts"]},
    {"name": "Marigold Hotel Jaipur", "ga4_id": "482893606", "domain": "hotelmarigoldjaipur.com", "keywords": ["hotelmarigoldjaipur","marigold","marigold hotel jaipur"]},
    {"name": "Aanandam Resort & Spa, Pushkar", "ga4_id": "468044493", "domain": "aanandamresortandspa.com", "keywords": ["aanandam","aanandam resort   spa  pushkar","aanandamresortandspa","pushkar","spa"]},
    {"name": "Downtown Hostels", "ga4_id": "481862358", "domain": "downtownhostels.in", "keywords": ["downtown","downtown hostels","downtownhostels","hostels"]},
    {"name": "Stay Inn Hospitality", "ga4_id": "459746878", "domain": "stayinnhospitality.in", "keywords": ["hospitality","stay","stay inn hospitality","stayinnhospitality"]},
    {"name": "Darza Resorts -Funland Day Outing", "ga4_id": "472460360", "domain": "darzaresorts.com", "keywords": ["darza","darza resorts  funland day outing","darzaresorts","day","funland","outing"]},
    {"name": "Frozen Fall Resort", "ga4_id": "458346533", "domain": "thefrozenfallresort.com", "keywords": ["fall","frozen","frozen fall resort","thefrozenfallresort"]},
    {"name": "Belihuloya Adventure Camp / River Garden Resort", "ga4_id": "459406200", "domain": "belihuloyasrilanka.com", "keywords": ["adventure","belihuloya","belihuloya adventure camp   river garden resort","belihuloyasrilanka","camp","river"]},
    {"name": "Mirage Hotel", "ga4_id": "467575042", "domain": "miragehotel.in", "keywords": ["mirage","mirage hotel","miragehotel"]},
    {"name": "Corbett Four Seasons, Ramnagar", "ga4_id": "449213677", "domain": "corbettfourseasons.com", "keywords": ["corbett","corbett four seasons  ramnagar","corbettfourseasons","four","ramnagar","seasons"]},
    {"name": "Cocoon Suites", "ga4_id": "459953191", "domain": "cocoonsuites.in", "keywords": ["cocoon","cocoon suites","cocoonsuites"]},
    {"name": "Flower Island Resort", "ga4_id": "491526720", "domain": "flowerislandresort.com", "keywords": ["flower","flower island resort","flowerislandresort","island"]},
    {"name": "Tranquil ABS Orchid Serviced Apartments, Bengaluru", "ga4_id": "459716314", "domain": "tranquilorchid.com", "keywords": ["abs","orchid","serviced","tranquil","tranquil abs orchid serviced apartments  bengaluru","tranquilorchid"]},
    {"name": "Hotel Ganga Maiya", "ga4_id": "435367099", "domain": "hotelgangamaiya.com", "keywords": ["ganga","hotel ganga maiya","hotelgangamaiya","maiya"]},
    {"name": "Chamong Chiabadi Resorts Private Limited", "ga4_id": "460950030", "domain": "chamongresorts.com", "keywords": ["chamong","chamong chiabadi resorts private limited","chamongresorts","chiabadi","limited","private"]},
    {"name": "Dip Holidays", "ga4_id": "465194788", "domain": "dipholidays.com", "keywords": ["dip","dip holidays","dipholidays","holidays"]},
    {"name": "Ramada Encore by Wyndham, Bhiwadi", "ga4_id": "469905424", "domain": "ramadaencorebhiwadi.com", "keywords": ["bhiwadi","encore","ramada","ramada encore by wyndham  bhiwadi","ramadaencorebhiwadi","wyndham"]},
    {"name": "Water Kingdom DNU", "ga4_id": "378387392", "domain": "waterkingdom.in", "keywords": ["kingdom","water","water kingdom dnu","waterkingdom"]},
    {"name": "Water Kingdom (Cloned Backup)", "ga4_id": "378387392", "domain": "9600_simplotel.com", "keywords": ["9600_simplotel","backup","cloned","kingdom","water","water kingdom  cloned backup"]},
    {"name": "Munnar Ice Queen Resort", "ga4_id": "461639859", "domain": "munnaricequeen.com", "keywords": ["ice","munnar","munnar ice queen resort","munnaricequeen","queen"]},
    {"name": "Crescent Resort, Goa", "ga4_id": "440389354", "domain": "unknown", "keywords": ["crescent","crescent resort  goa"]},
    {"name": "Crescent Resort, Sehore", "ga4_id": "440389354", "domain": "unknown", "keywords": ["crescent","crescent resort  sehore","sehore"]},
    {"name": "Earthitects Holiday Experiences", "ga4_id": "341861335", "domain": "earthitectsholidayexperiences.com", "keywords": ["earthitects","earthitects holiday experiences","earthitectsholidayexperiences","experiences","holiday"]},
    {"name": "Motel Divine International", "ga4_id": "465194352", "domain": "moteldivine.in", "keywords": ["divine","international","motel","motel divine international","moteldivine"]},
    {"name": "Shreyas Retreat", "ga4_id": "471603288", "domain": "shreyasretreat.com", "keywords": ["retreat","shreyas","shreyas retreat","shreyasretreat"]},
    {"name": "Casa Hotel and Suites", "ga4_id": "461987601", "domain": "casahotelandsuites.com", "keywords": ["casa","casa hotel and suites","casahotelandsuites"]},
    {"name": "Panna Vilas - A Lake Facing Boutique Hotel", "ga4_id": "465048377", "domain": "hotelpannavilas.com", "keywords": ["facing","hotelpannavilas","lake","panna","panna vilas   a lake facing boutique hotel","vilas"]},
    {"name": "The Tattva", "ga4_id": "365674566", "domain": "thetattva.in", "keywords": ["tattva","the tattva","thetattva"]},
    {"name": "Alba Hotels", "ga4_id": "461607089", "domain": "albahotels.co.in", "keywords": ["alba","alba hotels","albahotels"]},
    {"name": "Esaa Airport Hotel", "ga4_id": "461563263", "domain": "esaaairporthotel.com", "keywords": ["airport","esaa","esaa airport hotel","esaaairporthotel"]},
    {"name": "Trunk and Trolley, Gachibowli", "ga4_id": "395809928", "domain": "hotelathomesuites.com", "keywords": ["gachibowli","hotelathomesuites","trolley","trunk","trunk and trolley  gachibowli"]},
    {"name": "Nirantara Resort", "ga4_id": "465170300", "domain": "nirantararesort.com", "keywords": ["nirantara","nirantara resort","nirantararesort"]},
    {"name": "Hotel Sapphire Blue", "ga4_id": "462006411", "domain": "hotelsapphireblue.com", "keywords": ["blue","hotel sapphire blue","hotelsapphireblue","sapphire"]},
    {"name": "Hotel Heritage Shelter Resort", "ga4_id": "465943291", "domain": "hotelheritageshelters.com", "keywords": ["heritage","hotel heritage shelter resort","hotelheritageshelters","shelter"]},
    {"name": "Sandpebbles Bhitarkanika Jungle resorts", "ga4_id": "464531272", "domain": "bhitarkanikanationalpark.com", "keywords": ["bhitarkanika","bhitarkanikanationalpark","jungle","sandpebbles","sandpebbles bhitarkanika jungle resorts"]},
    {"name": "WoCAL Retreat Ke Ga", "ga4_id": "471136413", "domain": "wocal.camp", "keywords": ["retreat","wocal","wocal retreat ke ga"]},
    {"name": "Indie Stays", "ga4_id": "463888537", "domain": "indiestays.in", "keywords": ["indie","indie stays","indiestays","stays"]},
    {"name": "Indie Stays- DO NOT USE", "ga4_id": "463888537", "domain": "indiestays.in", "keywords": ["indie","indie stays  do not use","indiestays","stays"]},
    {"name": "Athiva Hotels & Resorts", "ga4_id": "508519290", "domain": "athiva.com", "keywords": ["athiva","athiva hotels   resorts"]},
    {"name": "Gemini Continental", "ga4_id": "471481969", "domain": "geminicontinental.com", "keywords": ["continental","gemini","gemini continental","geminicontinental"]},
    {"name": "Ramada Encore by Wyndham Gurugram Dwarka Expressway", "ga4_id": "479065443", "domain": "ramadaencoredwarkaexpressway.com", "keywords": ["encore","gurugram","ramada","ramada encore by wyndham gurugram dwarka expressway","ramadaencoredwarkaexpressway","wyndham"]},
    {"name": "Hotel 39, Jamaica", "ga4_id": "407222645", "domain": "hotel39jamaica.com", "keywords": ["hotel 39  jamaica","hotel39jamaica","jamaica"]},
    {"name": "The Grand Krishna Rooms", "ga4_id": "464975295", "domain": "grandkrishna.com", "keywords": ["grandkrishna","krishna","rooms","the grand krishna rooms"]},
    {"name": "Le Royale Palace", "ga4_id": "468362328", "domain": "leroyalepalace.com", "keywords": ["le royale palace","leroyalepalace","royale"]},
    {"name": "Hotel Amar Kothi Udaipur", "ga4_id": "464510978", "domain": "amarkothi.com", "keywords": ["amar","amarkothi","hotel amar kothi udaipur","kothi","udaipur"]},
    {"name": "Aanandam Resort & Spa, Pushkar", "ga4_id": "468044493", "domain": "aanandamresortandspa.com", "keywords": ["aanandam","aanandam resort   spa  pushkar","aanandamresortandspa","pushkar","spa"]},
    {"name": "Eden Homes", "ga4_id": "465165467", "domain": "edenhomes.in", "keywords": ["eden","eden homes","edenhomes","homes"]},
    {"name": "Sawai Hospitality", "ga4_id": "474036181", "domain": "sawaihospitality.com", "keywords": ["hospitality","sawai","sawai hospitality","sawaihospitality"]},
    {"name": "Benzz Park", "ga4_id": "467519703", "domain": "benzzpark.com", "keywords": ["benzz","benzz park","benzzpark","park"]},
    {"name": "LA Riqueza", "ga4_id": "444113454", "domain": "lariquezahotels.com", "keywords": ["la riqueza","lariquezahotels","riqueza"]},
    {"name": "The Woods Resorts", "ga4_id": "324464136", "domain": "thewoodsresorts.com", "keywords": ["the woods resorts","thewoodsresorts","woods"]},
    {"name": "Best Western Country Woods Hotel & Resort", "ga4_id": "517874106", "domain": "countrywoods.co.in", "keywords": ["best","best western country woods hotel   resort","country","countrywoods","western","woods"]},
    {"name": "Tranquil ABS Orchid Serviced Apartments, Bengaluru- Do NOT USE- 9576", "ga4_id": "459716314", "domain": "tranquilorchid.com", "keywords": ["abs","orchid","serviced","tranquil","tranquil abs orchid serviced apartments  bengaluru  do not use  9576","tranquilorchid"]},
    {"name": "Yashshree Hotels - REDIRECTS (DNU)", "ga4_id": "468401365", "domain": "yashshreehotels.in", "keywords": ["yashshree","yashshree hotels   redirects  dnu","yashshreehotels"]},
    {"name": "SFS Hotels", "ga4_id": "469098789", "domain": "sfshomebridge.in", "keywords": ["sfs","sfs hotels","sfshomebridge"]},
    {"name": "Al Manar Grand Hotel Apartment, Bur Dubai", "ga4_id": "468713713", "domain": "almanargrandhotel.com", "keywords": ["al manar grand hotel apartment  bur dubai","almanargrandhotel","apartment","bur","dubai","manar"]},
    {"name": "The Pelican Hotel, Cantonments, Accra", "ga4_id": "478772598", "domain": "thepelicanhotel.com", "keywords": ["accra","cantonments","pelican","the pelican hotel  cantonments  accra","thepelicanhotel"]},
    {"name": "Abaco Inn", "ga4_id": "458051713", "domain": "abacoinn.com", "keywords": ["abaco","abaco inn","abacoinn"]},
    {"name": "PEARL SMITH... A Serviced Apartments [A unit of SVENSMITH Hospitality]", "ga4_id": "467514811", "domain": "svensmithhospitality.com", "keywords": ["apartments","pearl","pearl smith    a serviced apartments  a unit of svensmith hospitality","serviced","smith","svensmithhospitality"]},
    {"name": "Accord Hotels and Resorts", "ga4_id": "250915045", "domain": "theaccordhotels.com", "keywords": ["accord","accord hotels and resorts","theaccordhotels"]},
    {"name": "The Qualia Resort Club & Brewery, Udaipur", "ga4_id": "467644444", "domain": "thequaliaudaipur.com", "keywords": ["brewery","club","qualia","the qualia resort club   brewery  udaipur","thequaliaudaipur","udaipur"]},
    {"name": "Sol Glow Resort, Nainital", "ga4_id": "457218955", "domain": "solglowhotels.com", "keywords": ["glow","nainital","sol","sol glow resort  nainital","solglowhotels"]},
    {"name": "Kaldan Samudhra Palace", "ga4_id": "376044302", "domain": "kaldanhotels.com", "keywords": ["kaldan","kaldan samudhra palace","kaldanhotels","samudhra"]},
    {"name": "The Lake Hill Group", "ga4_id": "469324083", "domain": "thelakehill.com", "keywords": ["hill","lake","the lake hill group","thelakehill"]},
    {"name": "Rajasthali Resort & Spa Jaipur", "ga4_id": "479930941", "domain": "rajasthaliresort.com", "keywords": ["rajasthali","rajasthali resort   spa jaipur","rajasthaliresort","spa"]},
    {"name": "Altitude Group of Hotels & Resorts", "ga4_id": "403214400", "domain": "altitudehotelsresorts.com", "keywords": ["altitude","altitude group of hotels   resorts","altitudehotelsresorts"]},
    {"name": "T24 Hospitality", "ga4_id": "477322470", "domain": "t-24.in", "keywords": ["hospitality","t-24","t24","t24 hospitality"]},
    {"name": "CALUX Hotels", "ga4_id": "469266522", "domain": "caluxhotels.com", "keywords": ["calux","calux hotels","caluxhotels"]},
    {"name": "Lazo Hotels", "ga4_id": "468751262", "domain": "lazoresorts.com", "keywords": ["lazo","lazo hotels","lazoresorts"]},
    {"name": "Hotel Utopia", "ga4_id": "470514684", "domain": "utopiadigha.com", "keywords": ["hotel utopia","utopia","utopiadigha"]},
    {"name": "IOSIS Spa & Wellness", "ga4_id": "291155964", "domain": "iosis-demo.com", "keywords": ["iosis","iosis spa   wellness","iosis-demo","spa","wellness"]},
    {"name": "BN Tourist Home", "ga4_id": "462651681", "domain": "bntouristhome.co", "keywords": ["bn tourist home","bntouristhome","home","tourist"]},
    {"name": "BLVD Club", "ga4_id": "477590429", "domain": "blvdclub.in", "keywords": ["blvd","blvd club","blvdclub","club"]},
    {"name": "Evara Spa & Resort", "ga4_id": "473871358", "domain": "evararesort.com", "keywords": ["evara","evara spa   resort","evararesort","spa"]},
    {"name": "Hotel Ganga Maiya 1732695833", "ga4_id": "435367099", "domain": "9923_simplotel.com", "keywords": ["1732695833","9923_simplotel","ganga","hotel ganga maiya 1732695833","maiya"]},
    {"name": "BN Tourist Home, Ooty", "ga4_id": "462651681", "domain": "bntouristhome.com", "keywords": ["bn tourist home  ooty","bntouristhome","home","ooty","tourist"]},
    {"name": "Hotel Regal Heaven, Pune", "ga4_id": "472431922", "domain": "hotelregalheaven.com", "keywords": ["heaven","hotel regal heaven  pune","hotelregalheaven","regal"]},
    {"name": "JC Residency", "ga4_id": "471398596", "domain": "jcresidency.com", "keywords": ["jc residency","jcresidency","residency"]},
    {"name": "Deccan Rooms", "ga4_id": "471119298", "domain": "deccanrooms.in", "keywords": ["deccan","deccan rooms","deccanrooms","rooms"]},
    {"name": "Qotel", "ga4_id": "477826250", "domain": "qotelstays.com", "keywords": ["qotel","qotelstays"]},
    {"name": "Poojari’s Nirantara", "ga4_id": "474528077", "domain": "poojarisnirantara.in", "keywords": ["nirantara","poojari","poojari s nirantara","poojarisnirantara"]},
    {"name": "Hotel Ramhan Palace", "ga4_id": "470797415", "domain": "hotelramhanpalace.com", "keywords": ["hotel ramhan palace","hotelramhanpalace","ramhan"]},
    {"name": "Maliekal Heritance Cherai Beach Cochin", "ga4_id": "470510319", "domain": "maliekalheritance.com", "keywords": ["beach","cherai","heritance","maliekal","maliekal heritance cherai beach cochin","maliekalheritance"]},
    {"name": "Hotel Harshali Residency, Khopoli (Nr. Imagica)", "ga4_id": "470984638", "domain": "hotelharshaliresidency.com", "keywords": ["harshali","hotel harshali residency  khopoli  nr  imagica","hotelharshaliresidency","imagica","khopoli","residency"]},
    {"name": "Rak Rooms", "ga4_id": "423901479", "domain": "rakrooms.in", "keywords": ["rak","rak rooms","rakrooms","rooms"]},
    {"name": "Snow Valley Resorts", "ga4_id": "471475602", "domain": "snowvalleyresorts.com", "keywords": ["snow","snow valley resorts","snowvalleyresorts","valley"]},
    {"name": "Nisarga Lake Resort", "ga4_id": "470116417", "domain": "nisargalakeresorttapola.in", "keywords": ["lake","nisarga","nisarga lake resort","nisargalakeresorttapola"]},
    {"name": "Villa Serenity Le Sejour, Pondicherry", "ga4_id": "478474512", "domain": "villaserenitylesejour.in", "keywords": ["pondicherry","sejour","serenity","villa","villa serenity le sejour  pondicherry","villaserenitylesejour"]},
    {"name": "BluSalzz Hospitality", "ga4_id": "476029008", "domain": "blusalzz.com", "keywords": ["blusalzz","blusalzz hospitality","hospitality"]},
    {"name": "WOW Bison Woods (DESH BUSINESS VENTURES PRIVATE LIMITED)", "ga4_id": "474705666", "domain": "bisonwoods.com", "keywords": ["bison","bisonwoods","desh","woods","wow","wow bison woods  desh business ventures private limited"]},
    {"name": "Regency Hotel, Mumbai", "ga4_id": "478375154", "domain": "theregencymumbai.in", "keywords": ["regency","regency hotel  mumbai","theregencymumbai"]},
    {"name": "Hotel Raai, Hosur- DO NOT USE", "ga4_id": "450325497", "domain": "hotelraai.com", "keywords": ["hosur","hotel raai  hosur  do not use","hotelraai","raai"]},
    {"name": "DLS Tehri Club Resort, Chamba", "ga4_id": "467575042", "domain": "unknown", "keywords": ["chamba","club","dls","dls tehri club resort  chamba","tehri"]},
    {"name": "DLS Hotels", "ga4_id": "425173972", "domain": "dlshotels.in", "keywords": ["dls","dls hotels","dlshotels"]},
    {"name": "Max Hotels", "ga4_id": "485011210", "domain": "maxhotelsindia.com", "keywords": ["max","max hotels","maxhotelsindia"]},
    {"name": "Hotel Shanker - Palatial Heritage Kathmandu", "ga4_id": "251220096", "domain": "shankerhotel.com.np", "keywords": ["heritage","hotel shanker   palatial heritage kathmandu","kathmandu","palatial","shanker","shankerhotel"]},
    {"name": "Bendheka – Cliff Front Cottages Coorg", "ga4_id": "479233373", "domain": "bendheka.com", "keywords": ["bendheka","bendheka   cliff front cottages coorg","cliff","cottages","front"]},
    {"name": "DLS The Classio, Rishikesh", "ga4_id": "467575042", "domain": "unknown", "keywords": ["classio","dls","dls the classio  rishikesh","rishikesh"]},
    {"name": "DLS Hotels The Rock Castle, Shimla", "ga4_id": "467575042", "domain": "unknown", "keywords": ["castle","dls","dls hotels the rock castle  shimla","rock","shimla"]},
    {"name": "DLS Ganga Bliss, Haridwar", "ga4_id": "467575042", "domain": "unknown", "keywords": ["bliss","dls","dls ganga bliss  haridwar","ganga","haridwar"]},
    {"name": "DLS Hillcrest Resort, Shimla", "ga4_id": "467575042", "domain": "unknown", "keywords": ["dls","dls hillcrest resort  shimla","hillcrest","shimla"]},
    {"name": "Casa Hotel Jubilee Hills", "ga4_id": "469882535", "domain": "casahoteljubileehills.com", "keywords": ["casa","casa hotel jubilee hills","casahoteljubileehills","hills","jubilee"]},
    {"name": "DLS Highland Resort & Spa, Mussoorie", "ga4_id": "467575042", "domain": "unknown", "keywords": ["dls","dls highland resort   spa  mussoorie","highland","mussoorie","spa"]},
    {"name": "Mud Haven Farm, Jhajjar", "ga4_id": "472641252", "domain": "mudhavenfarm.com", "keywords": ["farm","haven","jhajjar","mud","mud haven farm  jhajjar","mudhavenfarm"]},
    {"name": "Heaven In Himalayas", "ga4_id": "471889051", "domain": "heaveninhimalayas.com", "keywords": ["heaven","heaven in himalayas","heaveninhimalayas","himalayas"]},
    {"name": "M Pro Royal", "ga4_id": "479591431", "domain": "mpropalace.com", "keywords": ["m pro royal","mpropalace","pro","royal"]},
    {"name": "Stanley Revelation", "ga4_id": "491542625", "domain": "stanleyleisure.in", "keywords": ["revelation","stanley","stanley revelation","stanleyleisure"]},
    {"name": "The Kanila Resort, Karjat", "ga4_id": "478017894", "domain": "thekanila.com", "keywords": ["kanila","karjat","the kanila resort  karjat","thekanila"]},
    {"name": "Kara Hotel, Fort Kochi", "ga4_id": "474868278", "domain": "atkara.com", "keywords": ["atkara","fort","kara","kara hotel  fort kochi"]},
    {"name": "DLS Spring Valley Resort, Dharamshala", "ga4_id": "467575042", "domain": "unknown", "keywords": ["dharamshala","dls","dls spring valley resort  dharamshala","spring","valley"]},
    {"name": "Bamboo Saa Resorts & Spa- DO NOT USE", "ga4_id": "287972673", "domain": "bamboosaa.co", "keywords": ["bamboo","bamboo saa resorts   spa  do not use","bamboosaa","saa","spa"]},
    {"name": "DLS Grand Luxotica, Dehradun", "ga4_id": "467575042", "domain": "unknown", "keywords": ["dehradun","dls","dls grand luxotica  dehradun","luxotica"]},
    {"name": "DLS Hotel Shiva Sanctuary & Spa, Dharamshala", "ga4_id": "467575042", "domain": "unknown", "keywords": ["dls","dls hotel shiva sanctuary   spa  dharamshala","sanctuary","shiva","spa"]},
    {"name": "DLS Oak Bush, Mussoorie", "ga4_id": "467575042", "domain": "unknown", "keywords": ["bush","dls","dls oak bush  mussoorie","mussoorie","oak"]},
    {"name": "DLS Forest Vines Resort & Spa, Ramnagar (Jim Corbett)", "ga4_id": "467575042", "domain": "unknown", "keywords": ["dls","dls forest vines resort   spa  ramnagar  jim corbett","forest","spa","vines"]},
    {"name": "DLS The Emerald, Nainital", "ga4_id": "467575042", "domain": "unknown", "keywords": ["dls","dls the emerald  nainital","emerald","nainital"]},
    {"name": "DLS Nature Trinket Resort, Dalhousie", "ga4_id": "467575042", "domain": "unknown", "keywords": ["dalhousie","dls","dls nature trinket resort  dalhousie","nature","trinket"]},
    {"name": "DLS Meghavan Resort, Dharamshala", "ga4_id": "467575042", "domain": "unknown", "keywords": ["dharamshala","dls","dls meghavan resort  dharamshala","meghavan"]},
    {"name": "DLS Divine River Resort & Spa, Rishikesh", "ga4_id": "467575042", "domain": "unknown", "keywords": ["divine","dls","dls divine river resort   spa  rishikesh","river","spa"]},
    {"name": "DLS Ark Holiday Inn, Dalhousie", "ga4_id": "467575042", "domain": "unknown", "keywords": ["ark","dalhousie","dls","dls ark holiday inn  dalhousie","holiday"]},
    {"name": "DLS Dalhousie Valley Resort", "ga4_id": "467575042", "domain": "unknown", "keywords": ["dalhousie","dls","dls dalhousie valley resort","valley"]},
    {"name": "DLS Anupam Resort, Dharamshala", "ga4_id": "467575042", "domain": "unknown", "keywords": ["anupam","dharamshala","dls","dls anupam resort  dharamshala"]},
    {"name": "DLS Hotel Devlok, Manali", "ga4_id": "467575042", "domain": "unknown", "keywords": ["devlok","dls","dls hotel devlok  manali","manali"]},
    {"name": "DLS Kapoor Resort, Manali", "ga4_id": "467575042", "domain": "unknown", "keywords": ["dls","dls kapoor resort  manali","kapoor","manali"]},
    {"name": "DLS Park Grace, Haridwar", "ga4_id": "467575042", "domain": "unknown", "keywords": ["dls","dls park grace  haridwar","grace","haridwar","park"]},
    {"name": "DLS The Pearl, Mussoorie", "ga4_id": "467575042", "domain": "unknown", "keywords": ["dls","dls the pearl  mussoorie","mussoorie","pearl"]},
    {"name": "DLS La Serene Valley, Manali", "ga4_id": "467575042", "domain": "unknown", "keywords": ["dls","dls la serene valley  manali","manali","serene","valley"]},
    {"name": "DLS MJ River Resort, Rishikesh", "ga4_id": "467575042", "domain": "unknown", "keywords": ["dls","dls mj river resort  rishikesh","rishikesh","river"]},
    {"name": "Hotel Skylights", "ga4_id": "472357380", "domain": "skylightshotel.com", "keywords": ["hotel skylights","skylights","skylightshotel"]},
    {"name": "The Grand Hotel & Ballroom, McKinney", "ga4_id": "347673835", "domain": "grandhotelmckinney.com", "keywords": ["ballroom","grandhotelmckinney","mckinney","the grand hotel   ballroom  mckinney"]},
    {"name": "Hari Govinda's", "ga4_id": "479591458", "domain": "harigovindas.com", "keywords": ["govinda","hari","hari govinda s","harigovindas"]},
    {"name": "Hari Govinda's JN Stay, Ring Road", "ga4_id": "467575042", "domain": "unknown", "keywords": ["govinda","hari","hari govinda s jn stay  ring road","ring","stay"]},
    {"name": "DLS La Serene Valley (DNU)", "ga4_id": "467575042", "domain": "10109_simplotel.com", "keywords": ["10109_simplotel","dls","dls la serene valley  dnu","serene","valley"]},
    {"name": "DLS Tehri Club Resort (DNU)", "ga4_id": "467575042", "domain": "10110_simplotel.com", "keywords": ["10110_simplotel","club","dls","dls tehri club resort  dnu","tehri"]},
    {"name": "Paradise Isle Beach Resort, Udupi", "ga4_id": "483619755", "domain": "theparadiseisle.com", "keywords": ["beach","isle","paradise","paradise isle beach resort  udupi","theparadiseisle","udupi"]},
    {"name": "Namaste Corbett Resort and Spa", "ga4_id": "494659798", "domain": "namastecorbett.com", "keywords": ["corbett","namaste","namaste corbett resort and spa","namastecorbett","spa"]},
    {"name": "Cenneys Gateway - Pride of Salem", "ga4_id": "485576052", "domain": "hotelcenneys.com", "keywords": ["cenneys","cenneys gateway   pride of salem","gateway","hotelcenneys","pride","salem"]},
    {"name": "Eminence The Corbett", "ga4_id": "476028992", "domain": "eminencehotelsandresorts.com", "keywords": ["corbett","eminence","eminence the corbett","eminencehotelsandresorts"]},
    {"name": "Saccharum Safari Lodge, Kanha Tiger Reserve 1736407286", "ga4_id": "452609376", "domain": "dummy-domain-1736407286.com", "keywords": ["dummy-domain-1736407286","kanha","lodge","saccharum","saccharum safari lodge  kanha tiger reserve 1736407286","safari"]},
    {"name": "Lotus Leaf Boutique Hotel", "ga4_id": "473880789", "domain": "lotusleafhotel.com", "keywords": ["boutique","leaf","lotus","lotus leaf boutique hotel","lotusleafhotel"]},
    {"name": "Demo Palace extra demo", "ga4_id": "468442679", "domain": "dummy-domain-1736872354.com", "keywords": ["demo","demo palace extra demo","dummy-domain-1736872354","extra"]},
    {"name": "Nalapad Hotel Bangalore International", "ga4_id": "486848641", "domain": "nalapadhotels.com", "keywords": ["international","nalapad","nalapad hotel bangalore international","nalapadhotels"]},
    {"name": "Via Lakhela Resort & Spa, Kumbhalgarh", "ga4_id": "468442679", "domain": "unknown", "keywords": ["kumbhalgarh","lakhela","spa","via","via lakhela resort   spa  kumbhalgarh"]},
    {"name": "Brewery Gulch Inn & Spa", "ga4_id": "356908738", "domain": "brewerygulchinn.com", "keywords": ["brewery","brewery gulch inn   spa","brewerygulchinn","gulch","spa"]},
    {"name": "Hotel Grand Sigma", "ga4_id": "481725722", "domain": "hotelgrandsigma.com", "keywords": ["hotel grand sigma","hotelgrandsigma","sigma"]},
    {"name": "The Baron Group", "ga4_id": "475358010", "domain": "baronhotels.in", "keywords": ["baron","baronhotels","the baron group"]},
    {"name": "Panchabhuta Retreat", "ga4_id": "474535385", "domain": "panchabhutaretreat.com", "keywords": ["panchabhuta","panchabhuta retreat","panchabhutaretreat","retreat"]},
    {"name": "Lembranca Studios & Suites", "ga4_id": "477845658", "domain": "lembrancastays.com", "keywords": ["lembranca","lembranca studios   suites","lembrancastays","studios"]},
    {"name": "My Serene Hotels", "ga4_id": "477550113", "domain": "myserenehotels.com", "keywords": ["my serene hotels","myserenehotels","serene"]},
    {"name": "Mosaic Hotels", "ga4_id": "479064604", "domain": "mosaichotels.in", "keywords": ["mosaic","mosaic hotels","mosaichotels"]},
    {"name": "The Citi Residenci", "ga4_id": "486564852", "domain": "citiresidenci.com", "keywords": ["citi","citiresidenci","residenci","the citi residenci"]},
    {"name": "Clone for Dip  Holidays", "ga4_id": "465194788", "domain": "dummy-domain-1737373403.com", "keywords": ["clone","clone for dip  holidays","dip","dummy-domain-1737373403","for","holidays"]},
    {"name": "Shahpura Bagh", "ga4_id": "497655330", "domain": "shahpurabagh.com", "keywords": ["bagh","shahpura","shahpura bagh","shahpurabagh"]},
    {"name": "Adhyaya - Heritage Reverbed", "ga4_id": "483312689", "domain": "adhyayaheritage.com", "keywords": ["adhyaya","adhyaya   heritage reverbed","adhyayaheritage","heritage","reverbed"]},
    {"name": "Somani Hospitality", "ga4_id": "482474954", "domain": "somanihospitality.com", "keywords": ["hospitality","somani","somani hospitality","somanihospitality"]},
    {"name": "Bizz The Hotel", "ga4_id": "474660182", "domain": "bizzhotel.in", "keywords": ["bizz","bizz the hotel","bizzhotel"]},
    {"name": "Celebrity Resort", "ga4_id": "462886058", "domain": "celebrityhospitality.com", "keywords": ["celebrity","celebrity resort","celebrityhospitality"]},
    {"name": "Diamond Hotels", "ga4_id": "501936543", "domain": "diamondhotels.in", "keywords": ["diamond","diamond hotels","diamondhotels"]},
    {"name": "Hotel 1", "ga4_id": "421303271", "domain": "10189_simplotel.com", "keywords": ["10189_simplotel","hotel 1"]},
    {"name": "Best Western Plus Revanta Resort & Spa 1737702443", "ga4_id": "421303271", "domain": "dummy-domain-1737702443.com", "keywords": ["best","best western plus revanta resort   spa 1737702443","dummy-domain-1737702443","plus","revanta","western"]},
    {"name": "Hotel Ashok Nagpur", "ga4_id": "361271154", "domain": "thenagpurashok.com", "keywords": ["ashok","hotel ashok nagpur","nagpur","thenagpurashok"]},
    {"name": "The Soaltee", "ga4_id": "317872753", "domain": "soaltee.com", "keywords": ["soaltee","the soaltee"]},
    {"name": "Valley by Grassfield", "ga4_id": "513422113", "domain": "grassfieldhotelsandresorts.com", "keywords": ["grassfield","grassfieldhotelsandresorts","valley","valley by grassfield"]},
    {"name": "Hari Govinda's, Siddappa Square", "ga4_id": "467575042", "domain": "unknown", "keywords": ["govinda","hari","hari govinda s  siddappa square","siddappa","square"]},
    {"name": "Tisya Farms, Gurgaon", "ga4_id": "420301963", "domain": "tisyafarms.com", "keywords": ["farms","gurgaon","tisya","tisya farms  gurgaon","tisyafarms"]},
    {"name": "Astra Hotels and Suites", "ga4_id": "482484883", "domain": "astrahotels.in", "keywords": ["astra","astra hotels and suites","astrahotels"]},
    {"name": "Fragrant Nature Hotels 1738905272", "ga4_id": "400424534", "domain": "dummy-domain-1738905272.com", "keywords": ["1738905272","dummy-domain-1738905272","fragrant","fragrant nature hotels 1738905272","nature"]},
    {"name": "Hari Govinda's Express, Vijayanagar", "ga4_id": "467575042", "domain": "unknown", "keywords": ["express","govinda","hari","hari govinda s express  vijayanagar","vijayanagar"]},
    {"name": "Lords Hotels & Resorts", "ga4_id": "378950929", "domain": "lordshotels.com", "keywords": ["lords","lords hotels   resorts","lordshotels"]},
    {"name": "Surpura Bagh", "ga4_id": "486138767", "domain": "surpurabagh.com", "keywords": ["bagh","surpura","surpura bagh","surpurabagh"]},
    {"name": "Historic Tapoco Lodge", "ga4_id": "409657228", "domain": "tapoco.com", "keywords": ["historic","historic tapoco lodge","lodge","tapoco"]},
    {"name": "Chandragiri Hills Resort Kathmandu-Luxury in the Clouds", "ga4_id": "481947976", "domain": "chandragirihills.com", "keywords": ["chandragiri","chandragiri hills resort kathmandu luxury in the clouds","chandragirihills","hills","kathmandu","luxury"]},
    {"name": "Coorg Jungle Camp Backwater Resort, Kushalnagar", "ga4_id": "520292971", "domain": "coorgjunglecamp.com", "keywords": ["backwater","camp","coorg","coorg jungle camp backwater resort  kushalnagar","coorgjunglecamp","jungle"]},
    {"name": "Parampara Resort & Spa, Kushalnagar", "ga4_id": "386683555", "domain": "paramparacoorg.com", "keywords": ["kushalnagar","parampara","parampara resort   spa  kushalnagar","paramparacoorg","spa"]},
    {"name": "Parampara Residency, Kushalnagar", "ga4_id": "386935347", "domain": "parampararesidency.com", "keywords": ["kushalnagar","parampara","parampara residency  kushalnagar","parampararesidency","residency"]},
    {"name": "Hotel Altitude, Madikeri", "ga4_id": "386301458", "domain": "hotelaltitudecoorg.com", "keywords": ["altitude","hotel altitude  madikeri","hotelaltitudecoorg","madikeri"]},
    {"name": "Karma Chalets", "ga4_id": "437358968", "domain": "karmachalets.co.in", "keywords": ["chalets","karma","karma chalets","karmachalets"]},
    {"name": "Town Square Suites", "ga4_id": "483037340", "domain": "townsquaresuites.com", "keywords": ["square","town","town square suites","townsquaresuites"]},
    {"name": "Ramada Encore by Wyndham Gurugram Dwarka Expressway 1740118473", "ga4_id": "479065443", "domain": "dummy-domain-1740118473.com", "keywords": ["dummy-domain-1740118473","encore","gurugram","ramada","ramada encore by wyndham gurugram dwarka expressway 1740118473","wyndham"]},
    {"name": "Hotel Vishranti, Canal Road, Dehradun", "ga4_id": "487899590", "domain": "hotelvishranti.com", "keywords": ["canal","dehradun","hotel vishranti  canal road  dehradun","hotelvishranti","road","vishranti"]},
    {"name": "Ramada Encore by Wyndham Chandigarh Zirakpur", "ga4_id": "485717739", "domain": "ramadaencorechandigarhzirakpur.com", "keywords": ["chandigarh","encore","ramada","ramada encore by wyndham chandigarh zirakpur","ramadaencorechandigarhzirakpur","wyndham"]},
    {"name": "Ramada Encore by Wyndham Gurugram Dwarka Expressway 1740119966", "ga4_id": "479065443", "domain": "dummy-domain-1740119966.com", "keywords": ["dummy-domain-1740119966","encore","gurugram","ramada","ramada encore by wyndham gurugram dwarka expressway 1740119966","wyndham"]},
    {"name": "Indo Prime", "ga4_id": "482119833", "domain": "hotelindoprime.com", "keywords": ["hotelindoprime","indo","indo prime","prime"]},
    {"name": "Forest Escapes", "ga4_id": "468720948", "domain": "unknown", "keywords": ["escapes","forest","forest escapes"]},
    {"name": "Agreen Hotels", "ga4_id": "488631496", "domain": "agreenhotels.in", "keywords": ["agreen","agreen hotels","agreenhotels"]},
    {"name": "Nivasana Manali", "ga4_id": "479995366", "domain": "nivasana.com", "keywords": ["manali","nivasana","nivasana manali"]},
    {"name": "SeaFORT Beach Resort", "ga4_id": "480168078", "domain": "seafortresort.com", "keywords": ["beach","seafort","seafort beach resort","seafortresort"]},
    {"name": "The Chamomile Estate", "ga4_id": "468442679", "domain": "unknown", "keywords": ["chamomile","estate","the chamomile estate"]},
    {"name": "Ivory Destinations", "ga4_id": "489335703", "domain": "ivorydestinations.com", "keywords": ["destinations","ivory","ivory destinations","ivorydestinations"]},
    {"name": "The Evren, Vagator", "ga4_id": "494421519", "domain": "the-evren.com", "keywords": ["evren","the evren  vagator","the-evren","vagator"]},
    {"name": "Neem Sarai", "ga4_id": "481227066", "domain": "neemsaraisariska.com", "keywords": ["neem","neem sarai","neemsaraisariska","sarai"]},
    {"name": "Kyzen Hotels", "ga4_id": "501172592", "domain": "kyzenhotels.com", "keywords": ["kyzen","kyzen hotels","kyzenhotels"]},
    {"name": "Mazarine Hotel", "ga4_id": "481988983", "domain": "mazarinehotels.com", "keywords": ["mazarine","mazarine hotel","mazarinehotels"]},
    {"name": "The Qualia Resort Club & Brewery, Udaipur- DO NOT USE", "ga4_id": "467644444", "domain": "thequaliaudaipur.com", "keywords": ["brewery","club","qualia","the qualia resort club   brewery  udaipur  do not use","thequaliaudaipur","udaipur"]},
    {"name": "Airport Hotel Grand", "ga4_id": "481743909", "domain": "airporthotelgrand.com", "keywords": ["airport","airport hotel grand","airporthotelgrand"]},
    {"name": "Marigold Business Hotel", "ga4_id": "481854474", "domain": "marigoldhotel.co.in", "keywords": ["business","marigold","marigold business hotel","marigoldhotel"]},
    {"name": "Abaco Inn", "ga4_id": "458051713", "domain": "abacoinn.com", "keywords": ["abaco","abaco inn","abacoinn"]},
    {"name": "Foxoso Fiori Hotel", "ga4_id": "443076652", "domain": "unknown", "keywords": ["fiori","foxoso","foxoso fiori hotel"]},
    {"name": "Fiori Hotel, Jaipur 1741689737", "ga4_id": "443076652", "domain": "dummy-domain-1741689737.com", "keywords": ["1741689737","dummy-domain-1741689737","fiori","fiori hotel  jaipur 1741689737"]},
    {"name": "Vedikant Hotels & Resorts", "ga4_id": "491010577", "domain": "vedikant.com", "keywords": ["vedikant","vedikant hotels   resorts"]},
    {"name": "AamaGhati Resorts", "ga4_id": "489290216", "domain": "aamaghatiresort.com", "keywords": ["aamaghati","aamaghati resorts","aamaghatiresort"]},
    {"name": "Sukama Resort & Spa, Mukteshwar", "ga4_id": "498445989", "domain": "sukama.in", "keywords": ["mukteshwar","spa","sukama","sukama resort   spa  mukteshwar"]},
    {"name": "Woodstock Resorts, Coorg", "ga4_id": "494509920", "domain": "woodstockresorts.in", "keywords": ["coorg","woodstock","woodstock resorts  coorg","woodstockresorts"]},
    {"name": "King's Mansion, Candolim", "ga4_id": "528591319", "domain": "kingsmansiongoa.com", "keywords": ["candolim","king","king s mansion  candolim","kingsmansiongoa","mansion"]},
    {"name": "Kesar Bagh Palace, Chittorgarh", "ga4_id": "493931674", "domain": "kesarbaghchittor.com", "keywords": ["bagh","chittorgarh","kesar","kesar bagh palace  chittorgarh","kesarbaghchittor"]},
    {"name": "Central Mansions,  Phnom Penh", "ga4_id": "393779631", "domain": "centralmansions.com", "keywords": ["central","central mansions   phnom penh","centralmansions","mansions","penh","phnom"]},
    {"name": "Hotel CN Windsor", "ga4_id": "489889403", "domain": "cnwindsorhotel_10459.com", "keywords": ["cnwindsorhotel_10459","hotel cn windsor","windsor"]},
    {"name": "Bhagirathi by Atishay", "ga4_id": "485047875", "domain": "bhagirathibyatishay.com", "keywords": ["atishay","bhagirathi","bhagirathi by atishay","bhagirathibyatishay"]},
    {"name": "Hotel Park Inn, Nellore", "ga4_id": "486558710", "domain": "bhavanihotels.com", "keywords": ["bhavanihotels","hotel park inn  nellore","nellore","park"]},
    {"name": "Miros Hotels", "ga4_id": "496672434", "domain": "miroshotels.com", "keywords": ["miros","miros hotels","miroshotels"]},
    {"name": "White Sands Resort, Ladakh", "ga4_id": "484959510", "domain": "whitesandsnubra.com", "keywords": ["ladakh","sands","white","white sands resort  ladakh","whitesandsnubra"]},
    {"name": "Ayana Resorts, Hyderabad", "ga4_id": "483782656", "domain": "theayanaresorts.com", "keywords": ["ayana","ayana resorts  hyderabad","theayanaresorts"]},
    {"name": "Riverside Inn", "ga4_id": "468720948", "domain": "unknown", "keywords": ["riverside","riverside inn"]},
    {"name": "Conservancy Bungalow", "ga4_id": "468720948", "domain": "unknown", "keywords": ["bungalow","conservancy","conservancy bungalow"]},
    {"name": "Merlis Hotel, Coimbatore", "ga4_id": "490325284", "domain": "merlishotels.com", "keywords": ["coimbatore","merlis","merlis hotel  coimbatore","merlishotels"]},
    {"name": "Asian Suites- DO NOT USE", "ga4_id": "387089649", "domain": "asiansuites.in", "keywords": ["asian","asian suites  do not use","asiansuites"]},
    {"name": "River Sidde Inn", "ga4_id": "487396753", "domain": "riversiddeinn.com", "keywords": ["river","river sidde inn","riversiddeinn","sidde"]},
    {"name": "Hotel Nirvana Orchid", "ga4_id": "486455859", "domain": "hotelnirvanaorchid.com", "keywords": ["hotel nirvana orchid","hotelnirvanaorchid","nirvana","orchid"]},
    {"name": "Hotel Gold, Panipat", "ga4_id": "487771510", "domain": "hotelgoldpanipat.com", "keywords": ["gold","hotel gold  panipat","hotelgoldpanipat","panipat"]},
    {"name": "Black Rock Hotels & Resorts", "ga4_id": "489965583", "domain": "blackrockhotels.com", "keywords": ["black","black rock hotels   resorts","blackrockhotels","rock"]},
    {"name": "ARNISA A Boutique Hotel", "ga4_id": "494895638", "domain": "arnisahotels.com", "keywords": ["arnisa","arnisa a boutique hotel","arnisahotels","boutique"]},
    {"name": "Elysian Vale", "ga4_id": "485774709", "domain": "elysianvale.com", "keywords": ["elysian","elysian vale","elysianvale","vale"]},
    {"name": "Wind Chalet", "ga4_id": "468720948", "domain": "unknown", "keywords": ["chalet","wind","wind chalet"]},
    {"name": "The Verda Hotels & Resorts", "ga4_id": "494122578", "domain": "theverda.com", "keywords": ["the verda hotels   resorts","theverda","verda"]},
    {"name": "Orsino Hotels & Resort", "ga4_id": "489584034", "domain": "orsinohotels.com", "keywords": ["orsino","orsino hotels   resort","orsinohotels"]},
    {"name": "Hotel Park Inn (do not use)", "ga4_id": "483312689", "domain": "dummy-domain-1743491494.com", "keywords": ["dummy-domain-1743491494","hotel park inn  do not use","park"]},
    {"name": "Hartstone Inn", "ga4_id": "409626503", "domain": "hartstoneinn.com", "keywords": ["hartstone","hartstone inn","hartstoneinn"]},
    {"name": "Miros Hotels - DO NOT USE", "ga4_id": "496672434", "domain": "miroshotels2.com", "keywords": ["miros","miros hotels   do not use","miroshotels2"]},
    {"name": "GoSavvy Executive Residences - Three Bedroom", "ga4_id": "484602892", "domain": "residences.gosavvy.in", "keywords": ["executive","gosavvy","gosavvy executive residences   three bedroom","residences","three"]},
    {"name": "Lords parent clone", "ga4_id": "378950929", "domain": "dummy-domain-1743584290.com", "keywords": ["clone","dummy-domain-1743584290","lords","lords parent clone","parent"]},
    {"name": "Strawberry King Resort, Mahabaleshwar", "ga4_id": "489138074", "domain": "strawberrykingresort.com", "keywords": ["king","mahabaleshwar","strawberry","strawberry king resort  mahabaleshwar","strawberrykingresort"]},
    {"name": "Hotel Vishwam Residency", "ga4_id": "486725347", "domain": "vishwamresidency.com", "keywords": ["hotel vishwam residency","residency","vishwam","vishwamresidency"]},
    {"name": "jüSTa Hotels & Resorts", "ga4_id": "283060568", "domain": "justahotels.com", "keywords": ["justahotels","jüsta","jüsta hotels   resorts"]},
    {"name": "Ana Hotels and Resorts", "ga4_id": "486188595", "domain": "anahotelsandresorts.com", "keywords": ["ana","ana hotels and resorts","anahotelsandresorts"]},
    {"name": "Shabari Hotel - DO NOT USE & Spa, Pelling (demo) 1743679430", "ga4_id": "386389635", "domain": "dummy-domain-1743679430.com", "keywords": ["demo","dummy-domain-1743679430","pelling","shabari","shabari hotel   do not use   spa  pelling  demo  1743679430","spa"]},
    {"name": "Ramada by Wyndham Ghaziabad Vasundhara (A Unit of IP Constructions Pvt. Ltd.)", "ga4_id": "487212961", "domain": "ramadavasundhara.com", "keywords": ["ghaziabad","ramada","ramada by wyndham ghaziabad vasundhara  a unit of ip constructions pvt  ltd","ramadavasundhara","vasundhara","wyndham"]},
    {"name": "Kssemya", "ga4_id": "488956828", "domain": "kssemya.in", "keywords": ["kssemya"]},
    {"name": "Mansha Hotels", "ga4_id": "408996334", "domain": "manshahotels.com", "keywords": ["mansha","mansha hotels","manshahotels"]},
    {"name": "Nirvana Gateway", "ga4_id": "517887647", "domain": "nirvanahotelsandresorts.com", "keywords": ["gateway","nirvana","nirvana gateway","nirvanahotelsandresorts"]},
    {"name": "Casa Morada", "ga4_id": "409639628", "domain": "casamorada.com", "keywords": ["casa","casa morada","casamorada","morada"]},
    {"name": "Thavika Onila Resort, Yelagiri", "ga4_id": "485058971", "domain": "thavikahotelsandresorts.com", "keywords": ["onila","thavika","thavika onila resort  yelagiri","thavikahotelsandresorts","yelagiri"]},
    {"name": "Sanctum Suites - DO NOT USE", "ga4_id": "425173972", "domain": "dummy-domain-1744191183.com", "keywords": ["dummy-domain-1744191183","sanctum","sanctum suites   do not use"]},
    {"name": "Sanctum Suites Richmond Road, Bangalore", "ga4_id": "467575042", "domain": "unknown", "keywords": ["richmond","road","sanctum","sanctum suites richmond road  bangalore"]},
    {"name": "Siri Ambari Resorts & Spa", "ga4_id": "510391347", "domain": "siriambariresortsandspa.com", "keywords": ["ambari","siri","siri ambari resorts   spa","siriambariresortsandspa","spa"]},
    {"name": "Express Inn Hotels & Resorts", "ga4_id": "425173972", "domain": "expressinnindia.com", "keywords": ["express","express inn hotels   resorts","expressinnindia"]},
    {"name": "Freesia Luxury Villa by Express Inn", "ga4_id": "467575042", "domain": "unknown", "keywords": ["express","freesia","freesia luxury villa by express inn","luxury","villa"]},
    {"name": "The Citrine, Bangalore", "ga4_id": "514962320", "domain": "thecitrinehotel.com", "keywords": ["citrine","the citrine  bangalore","thecitrinehotel"]},
    {"name": "Hotel Bangalore Gate", "ga4_id": "486191102", "domain": "hotelbangaloregate.com", "keywords": ["gate","hotel bangalore gate","hotelbangaloregate"]},
    {"name": "BNGV Grandeur Hotel & Banquets", "ga4_id": "490803875", "domain": "bngvgrandeurhotel.com", "keywords": ["banquets","bngv","bngv grandeur hotel   banquets","bngvgrandeurhotel","grandeur"]},
    {"name": "Orsino Spa Resort ( DNU)", "ga4_id": "467379259", "domain": "10625_simplotel.com", "keywords": ["10625_simplotel","orsino","orsino spa resort   dnu","spa"]},
    {"name": "Wyndham Garden", "ga4_id": "489282917", "domain": "wyndhamgardenjimcorbettchoi.com", "keywords": ["garden","wyndham","wyndham garden","wyndhamgardenjimcorbettchoi"]},
    {"name": "Sanctum Suites Indiranagar, Bangalore", "ga4_id": "467575042", "domain": "unknown", "keywords": ["indiranagar","sanctum","sanctum suites indiranagar  bangalore"]},
    {"name": "Sanctum Suites Hotels Bangalore 1744876417 (Clone, DNU)", "ga4_id": "326512323", "domain": "dummy-domain-1744876417.com", "keywords": ["1744876417","clone","dummy-domain-1744876417","sanctum","sanctum suites hotels bangalore 1744876417  clone  dnu"]},
    {"name": "Sanctum Suites Domlur, Bangalore", "ga4_id": "467575042", "domain": "unknown", "keywords": ["domlur","sanctum","sanctum suites domlur  bangalore"]},
    {"name": "Sanctum Suites BEL Road, Bangalore", "ga4_id": "467575042", "domain": "unknown", "keywords": ["bel","road","sanctum","sanctum suites bel road  bangalore"]},
    {"name": "Sanctum Suites Whitefield, Bangalore", "ga4_id": "467575042", "domain": "unknown", "keywords": ["sanctum","sanctum suites whitefield  bangalore","whitefield"]},
    {"name": "Ilara Hotels & Spa", "ga4_id": "500756098", "domain": "ilarahotels.com", "keywords": ["ilara","ilara hotels   spa","ilarahotels","spa"]},
    {"name": "Melior Inn", "ga4_id": "489093516", "domain": "meliorinn.com", "keywords": ["melior","melior inn","meliorinn"]},
    {"name": "Crescent Spa & Resort, Indore 1745393853", "ga4_id": "440389354", "domain": "10653_simplotel.com", "keywords": ["10653_simplotel","1745393853","crescent","crescent spa   resort  indore 1745393853","indore","spa"]},
    {"name": "Hotel Shashinag Residency", "ga4_id": "493950166", "domain": "hotelshashinagresidency.com", "keywords": ["hotel shashinag residency","hotelshashinagresidency","residency","shashinag"]},
    {"name": "Kailash Garden OMR and Kailash Conventions ECR (design layout)", "ga4_id": "468720948", "domain": "10668_simplotel.com", "keywords": ["10668_simplotel","garden","kailash","kailash garden omr and kailash conventions ecr  design layout","omr"]},
    {"name": "JVR Stays", "ga4_id": "494003059", "domain": "jvrstays.com", "keywords": ["jvr","jvr stays","jvrstays","stays"]},
    {"name": "Morni Singh", "ga4_id": "489975324", "domain": "mornisinghs.wcard.me", "keywords": ["morni","morni singh","mornisinghs","singh"]},
    {"name": "The Meriton", "ga4_id": "498664401", "domain": "meritonhotel.com", "keywords": ["meriton","meritonhotel","the meriton"]},
    {"name": "Kailash Garden OMR and Kailash Conventions ECR (Design llayout)", "ga4_id": "467575042", "domain": "10679_simplotel.com", "keywords": ["10679_simplotel","garden","kailash","kailash garden omr and kailash conventions ecr  design llayout","omr"]},
    {"name": "Hotel Highway King", "ga4_id": "499739458", "domain": "hotelhighwayking.com", "keywords": ["highway","hotel highway king","hotelhighwayking","king"]},
    {"name": "Grande Bay Resort & Spa, Mamallapuram", "ga4_id": "506030219", "domain": "grandebayresort.in", "keywords": ["bay","grande","grande bay resort   spa  mamallapuram","grandebayresort","mamallapuram","spa"]},
    {"name": "Vaasta Vagamon", "ga4_id": "494016467", "domain": "vaastavagamon.com", "keywords": ["vaasta","vaasta vagamon","vaastavagamon","vagamon"]},
    {"name": "RD's Nature Retreat, Bangalore", "ga4_id": "313218246", "domain": "rdsnatureretreat.com", "keywords": ["nature","rd s nature retreat  bangalore","rdsnatureretreat","retreat"]},
    {"name": "RainForest Resort, Port Blair, Andaman and Nicobar Islands", "ga4_id": "494101837", "domain": "rainforestresort.in", "keywords": ["andaman","blair","port","rainforest","rainforest resort  port blair  andaman and nicobar islands","rainforestresort"]},
    {"name": "Sea Hills Hotels & Resorts", "ga4_id": "496437907", "domain": "seahillshotels.com", "keywords": ["hills","sea","sea hills hotels   resorts","seahillshotels"]},
    {"name": "Hotel Vishranti Canal Road, Dehradun- Redirects", "ga4_id": "486587509", "domain": "vishrantiresorts.com", "keywords": ["canal","dehradun","hotel vishranti canal road  dehradun  redirects","road","vishranti","vishrantiresorts"]},
    {"name": "Hotel Mamallaa Heritage, Mahabalipuram", "ga4_id": "506042253", "domain": "hotelmamallaheritage.com", "keywords": ["heritage","hotel mamallaa heritage  mahabalipuram","hotelmamallaheritage","mahabalipuram","mamallaa"]},
    {"name": "Kaashvi Residency - Managed by Atithi House", "ga4_id": "488595109", "domain": "kaashviresidency.com", "keywords": ["atithi","kaashvi","kaashvi residency   managed by atithi house","kaashviresidency","managed","residency"]},
    {"name": "Khas Bagh, Jaipur", "ga4_id": "499444896", "domain": "khasbagh.com", "keywords": ["bagh","khas","khas bagh  jaipur","khasbagh"]},
    {"name": "Dream Vision Guest House, Diu", "ga4_id": "494334074", "domain": "dreamvisionstays.com", "keywords": ["dream","dream vision guest house  diu","dreamvisionstays","guest","house","vision"]},
    {"name": "Ramada by Wyndham Bodh Gaya Mahabodhi", "ga4_id": "518944979", "domain": "ramadabodhgayamahabodhi.com", "keywords": ["bodh","gaya","ramada","ramada by wyndham bodh gaya mahabodhi","ramadabodhgayamahabodhi","wyndham"]},
    {"name": "Anupam Hoteliers (DO NOT USE)", "ga4_id": "500730436", "domain": "anupamhoteliersltd.com", "keywords": ["anupam","anupam hoteliers  do not use","anupamhoteliersltd","hoteliers"]},
    {"name": "The Elanza Hotel", "ga4_id": "498622782", "domain": "theelanzahotels.com", "keywords": ["elanza","the elanza hotel","theelanzahotels"]},
    {"name": "Tranquil Group", "ga4_id": "489546113", "domain": "tranquilhotels.in", "keywords": ["tranquil","tranquil group","tranquilhotels"]},
    {"name": "Tranquil Piedmont Estates & Resort, Lonavala", "ga4_id": "489607658", "domain": "tranquilpiedmont.com", "keywords": ["estates","lonavala","piedmont","tranquil","tranquil piedmont estates   resort  lonavala","tranquilpiedmont"]},
    {"name": "Girivihar Dining & Holiday Club", "ga4_id": "489982330", "domain": "giriviharlonavala.com", "keywords": ["club","dining","girivihar","girivihar dining   holiday club","giriviharlonavala","holiday"]},
    {"name": "Mountain Shadows Wayanad", "ga4_id": "491367882", "domain": "mountainshadows.in", "keywords": ["mountain","mountain shadows wayanad","mountainshadows","shadows","wayanad"]},
    {"name": "Sea Hills Resort, Swaraj Dweep (Havelock)", "ga4_id": "468720948", "domain": "unknown", "keywords": ["dweep","hills","sea","sea hills resort  swaraj dweep  havelock","swaraj"]},
    {"name": "The Isle By Wonderla", "ga4_id": "357767337", "domain": "wonderla.com", "keywords": ["isle","the isle by wonderla","wonderla"]},
    {"name": "De Soul Santé Hotels & Resorts", "ga4_id": "490733605", "domain": "desoulsante.com", "keywords": ["de soul santé hotels   resorts","desoulsante","santé","soul"]},
    {"name": "Vedic Village Spa Resort, Kolkata", "ga4_id": "501495917", "domain": "thevedicvillage.com", "keywords": ["spa","thevedicvillage","vedic","vedic village spa resort  kolkata","village"]},
    {"name": "Lighthouse Waterpark & Resort, Nagpur", "ga4_id": "525078751", "domain": "lighthousewaterpark.com", "keywords": ["lighthouse","lighthouse waterpark   resort  nagpur","lighthousewaterpark","nagpur","waterpark"]},
    {"name": "Retreat Hospitality", "ga4_id": "501182628", "domain": "retreathospitality.com", "keywords": ["hospitality","retreat","retreat hospitality","retreathospitality"]},
    {"name": "Daksh Hotels & Resorts", "ga4_id": "504899774", "domain": "dakshhotels.com", "keywords": ["daksh","daksh hotels   resorts","dakshhotels"]},
    {"name": "Daksh Eden Greenz, Sasan Gir", "ga4_id": "468720948", "domain": "unknown", "keywords": ["daksh","daksh eden greenz  sasan gir","eden","greenz","sasan"]},
    {"name": "Hyphen Hotels", "ga4_id": "512092759", "domain": "hyphenhotels.com", "keywords": ["hyphen","hyphen hotels","hyphenhotels"]},
    {"name": "Tamarind Hills Resort and Villas - Antigua", "ga4_id": "317930936", "domain": "tamarindhills.com", "keywords": ["antigua","hills","tamarind","tamarind hills resort and villas   antigua","tamarindhills","villas"]},
    {"name": "Lords Hotels & Resorts 1748613735", "ga4_id": "378950929", "domain": "dummy-domain-1748613735.com", "keywords": ["1748613735","dummy-domain-1748613735","lords","lords hotels   resorts 1748613735"]},
    {"name": "Hotel Tip Top International", "ga4_id": "494148498", "domain": "tiptophotel.in", "keywords": ["hotel tip top international","international","tip","tiptophotel","top"]},
    {"name": "Pipul Hotels & Resorts", "ga4_id": "517378094", "domain": "pipulhotelsandresorts.com", "keywords": ["pipul","pipul hotels   resorts","pipulhotelsandresorts"]},
    {"name": "Highflyer Consultants", "ga4_id": "503564900", "domain": "highflyerconsultants.com", "keywords": ["consultants","highflyer","highflyer consultants","highflyerconsultants"]},
    {"name": "Kadamb Kuteer, Vrindavan", "ga4_id": "528061481", "domain": "kadambkuteer.com", "keywords": ["kadamb","kadamb kuteer  vrindavan","kadambkuteer","kuteer","vrindavan"]},
    {"name": "DND", "ga4_id": "407222645", "domain": "dummy-domain-1749434818.com", "keywords": ["dnd","dummy-domain-1749434818"]},
    {"name": "Altamont Court, Jamaica", "ga4_id": "386282594", "domain": "altamontcourt.com", "keywords": ["altamont","altamont court  jamaica","altamontcourt","court","jamaica"]},
    {"name": "Hotel Citi Grand, Varanasi", "ga4_id": "465194788", "domain": "dummy-domain-1749450397.com", "keywords": ["citi","dummy-domain-1749450397","hotel citi grand  varanasi","varanasi"]},
    {"name": "Crescent Resort, Goa 1749456270", "ga4_id": "440389354", "domain": "10841_simplotel.com", "keywords": ["10841_simplotel","1749456270","crescent","crescent resort  goa 1749456270"]},
    {"name": "Crescent Resort, Sehore 1749456270", "ga4_id": "440389354", "domain": "10842_simplotel.com", "keywords": ["10842_simplotel","1749456270","crescent","crescent resort  sehore 1749456270","sehore"]},
    {"name": "Hotel Sahara Tree", "ga4_id": "496234892", "domain": "hotelsaharatree.com", "keywords": ["hotel sahara tree","hotelsaharatree","sahara","tree"]},
    {"name": "The Evren, Vagator (DO NOT USE)", "ga4_id": "494421519", "domain": "the-evren.com", "keywords": ["evren","the evren  vagator  do not use","the-evren","vagator"]},
    {"name": "IQ Hotels & Resort", "ga4_id": "494026256", "domain": "theiqhotels.com", "keywords": ["iq hotels   resort","theiqhotels"]},
    {"name": "Hotel Landmark", "ga4_id": "495206433", "domain": "hotellandmarkchd.in", "keywords": ["hotel landmark","hotellandmarkchd","landmark"]},
    {"name": "Pravasa Hotels", "ga4_id": "508272275", "domain": "pravasahotels.com", "keywords": ["pravasa","pravasa hotels","pravasahotels"]},
    {"name": "Hotel Exotic, Amritsar", "ga4_id": "502139579", "domain": "hotelexotic.in", "keywords": ["amritsar","exotic","hotel exotic  amritsar","hotelexotic"]},
    {"name": "A Stone's Throw Away", "ga4_id": "510621989", "domain": "astonesthrowaway.com", "keywords": ["a stone s throw away","astonesthrowaway","away","stone","throw"]},
    {"name": "Megha Resort & Villas, Dehradun-Where Nature Pampers You", "ga4_id": "510065187", "domain": "megharesortandvillas.com", "keywords": ["dehradun","megha","megha resort   villas  dehradun where nature pampers you","megharesortandvillas","villas","where"]},
    {"name": "Shilton Hotels", "ga4_id": "496441576", "domain": "shiltonhotels.com", "keywords": ["shilton","shilton hotels","shiltonhotels"]},
    {"name": "Fireflies Resorts, Kabini", "ga4_id": "497197715", "domain": "firefliesresorts.com", "keywords": ["fireflies","fireflies resorts  kabini","firefliesresorts","kabini"]},
    {"name": "Ramada by Wyndham Sonipat Murthal", "ga4_id": "497723111", "domain": "ramadasonipatmurthal.com", "keywords": ["murthal","ramada","ramada by wyndham sonipat murthal","ramadasonipatmurthal","sonipat","wyndham"]},
    {"name": "Purvi Discovery", "ga4_id": "487683044", "domain": "purvidiscovery.com", "keywords": ["discovery","purvi","purvi discovery","purvidiscovery"]},
    {"name": "Revtree Hotels", "ga4_id": "495942038", "domain": "revtreehotels.com", "keywords": ["revtree","revtree hotels","revtreehotels"]},
    {"name": "Paradise Lagoon Resort, Udupi", "ga4_id": "514307510", "domain": "paradiselagoon.co.in", "keywords": ["lagoon","paradise","paradise lagoon resort  udupi","paradiselagoon","udupi"]},
    {"name": "Paradise Wild Hills Resort, Kollur", "ga4_id": "507106337", "domain": "paradisewildhills.com", "keywords": ["hills","kollur","paradise","paradise wild hills resort  kollur","paradisewildhills","wild"]},
    {"name": "Daksh Resort & Amusement Park, Sasan Gir", "ga4_id": "468720948", "domain": "unknown", "keywords": ["amusement","daksh","daksh resort   amusement park  sasan gir","park","sasan"]},
    {"name": "Infiniti Hotel, Indore", "ga4_id": "496304261", "domain": "hotelinfiniti.com", "keywords": ["hotelinfiniti","indore","infiniti","infiniti hotel  indore"]},
    {"name": "Mayfair Cafe & Suites Old Shell", "ga4_id": "495401204", "domain": "mayfairdalhousie.com", "keywords": ["cafe","mayfair","mayfair cafe   suites old shell","mayfairdalhousie","old","shell"]},
    {"name": "Monday Hotels", "ga4_id": "460515353", "domain": "mondayhotels.com", "keywords": ["monday","monday hotels","mondayhotels"]},
    {"name": "Funky Leopard Safari Lodge (LOCAL)", "ga4_id": "448965379", "domain": "yalaparksrilanka.com", "keywords": ["funky","funky leopard safari lodge  local","leopard","lodge","safari","yalaparksrilanka"]},
    {"name": "Oro The Estate", "ga4_id": "496376260", "domain": "orocircle.com", "keywords": ["estate","oro","oro the estate","orocircle"]},
    {"name": "Daksh The Madhuvan Suites, Dwarka", "ga4_id": "468720948", "domain": "unknown", "keywords": ["daksh","daksh the madhuvan suites  dwarka","dwarka","madhuvan"]},
    {"name": "Daksh The Grand Goverdhan, Dwarka", "ga4_id": "468720948", "domain": "unknown", "keywords": ["daksh","daksh the grand goverdhan  dwarka","dwarka","goverdhan"]},
    {"name": "Hotel Presidency Kochi, City Centre", "ga4_id": "496960187", "domain": "presidencyhotel.com", "keywords": ["centre","city","hotel presidency kochi  city centre","presidency","presidencyhotel"]},
    {"name": "Mahendra Niwas", "ga4_id": "506576188", "domain": "mahendraniwas.in", "keywords": ["mahendra","mahendra niwas","mahendraniwas","niwas"]},
    {"name": "Trunk and Trolley, Nanakramguda, A Luxury Boutique Group of Hotels", "ga4_id": "495226724", "domain": "unknown", "keywords": ["luxury","nanakramguda","trolley","trunk","trunk and trolley  nanakramguda  a luxury boutique group of hotels"]},
    {"name": "Mayfair Café & Suites, Dalhousie", "ga4_id": "495401204", "domain": "mayfairdalhousie.com", "keywords": ["café","dalhousie","mayfair","mayfair café   suites  dalhousie","mayfairdalhousie"]},
    {"name": "GRT Hotels & Resorts", "ga4_id": "464163304", "domain": "grthotels.com", "keywords": ["grt","grt hotels   resorts","grthotels"]},
    {"name": "Arch Group of Hotels", "ga4_id": "498502171", "domain": "archgroupofhotels.com", "keywords": ["arch","arch group of hotels","archgroupofhotels"]},
    {"name": "Hotel Willow Banks", "ga4_id": "498686535", "domain": "willowbanks.com", "keywords": ["banks","hotel willow banks","willow","willowbanks"]},
    {"name": "Papaya Tree Hotels", "ga4_id": "512271946", "domain": "papayatreehotels.com", "keywords": ["papaya","papaya tree hotels","papayatreehotels","tree"]},
    {"name": "My Serene Hotels 1752754655", "ga4_id": "477550113", "domain": "dummy-domain-1752754655.com", "keywords": ["1752754655","dummy-domain-1752754655","my serene hotels 1752754655","serene"]},
    {"name": "Polo Hotels and Resorts", "ga4_id": "506023095", "domain": "polohotelsandresorts.com", "keywords": ["polo","polo hotels and resorts","polohotelsandresorts"]},
    {"name": "Mahua Boutique Homestay", "ga4_id": "498631266", "domain": "themahua.com", "keywords": ["boutique","homestay","mahua","mahua boutique homestay","themahua"]},
    {"name": "A & M Rooms and Residences", "ga4_id": "522055745", "domain": "aandmhotels.com", "keywords": ["a   m rooms and residences","aandmhotels","residences","rooms"]},
    {"name": "Royal Group of Hotels", "ga4_id": "509730114", "domain": "royalgroupofhotels.com", "keywords": ["royal","royal group of hotels","royalgroupofhotels"]},
    {"name": "Lime Tree Hotels & Service Apartment Private Limited- DO NOT USE", "ga4_id": "374794749", "domain": "limetreehotels.com", "keywords": ["apartment","lime","lime tree hotels   service apartment private limited  do not use","limetreehotels","service","tree"]},
    {"name": "The Palm Aryan Hotels", "ga4_id": "501950909", "domain": "thepalmaryanhotels.com", "keywords": ["aryan","palm","the palm aryan hotels","thepalmaryanhotels"]},
    {"name": "Simplotel clone", "ga4_id": "375525753", "domain": "dummy-domain-1753442560.com", "keywords": ["clone","dummy-domain-1753442560","simplotel","simplotel clone"]},
    {"name": "Osian Valley Resort & Spa, Kumbhalgarh", "ga4_id": "506632577", "domain": "osianvalleyresort.com", "keywords": ["kumbhalgarh","osian","osian valley resort   spa  kumbhalgarh","osianvalleyresort","spa","valley"]},
    {"name": "Jaypore360 Homestay", "ga4_id": "509196601", "domain": "jaypore360homestay.com", "keywords": ["homestay","jaypore360","jaypore360 homestay","jaypore360homestay"]},
    {"name": "The Pinnacle - Electronic city, Bengaluru", "ga4_id": "506304459", "domain": "thepinnaclestay.com", "keywords": ["bengaluru","city","electronic","pinnacle","the pinnacle   electronic city  bengaluru","thepinnaclestay"]},
    {"name": "Amulya Regency", "ga4_id": "499701211", "domain": "amulyaregency.com", "keywords": ["amulya","amulya regency","amulyaregency","regency"]},
    {"name": "Copper Edge - Eco Resort, Coorg", "ga4_id": "504729762", "domain": "copperedge.in", "keywords": ["coorg","copper","copper edge   eco resort  coorg","copperedge","eco","edge"]},
    {"name": "Freesia Residency by Express Inn Ghansoli", "ga4_id": "467575042", "domain": "unknown", "keywords": ["express","freesia","freesia residency by express inn ghansoli","ghansoli","residency"]},
    {"name": "Freesia Residency by Express Inn Nashik", "ga4_id": "467575042", "domain": "unknown", "keywords": ["express","freesia","freesia residency by express inn nashik","nashik","residency"]},
    {"name": "Freesia By Express Inn Borivali", "ga4_id": "467575042", "domain": "unknown", "keywords": ["borivali","express","freesia","freesia by express inn borivali"]},
    {"name": "Freesia By Express Inn Boisar", "ga4_id": "467575042", "domain": "unknown", "keywords": ["boisar","express","freesia","freesia by express inn boisar"]},
    {"name": "Freesia Resort by Express Inn", "ga4_id": "467575042", "domain": "unknown", "keywords": ["express","freesia","freesia resort by express inn"]},
    {"name": "Express Inn Nashik", "ga4_id": "467575042", "domain": "unknown", "keywords": ["express","express inn nashik","nashik"]},
    {"name": "Estherea Hotels & Resorts", "ga4_id": "499124566", "domain": "esthereahotels.com", "keywords": ["estherea","estherea hotels   resorts","esthereahotels"]},
    {"name": "Simplotel 1753816246", "ga4_id": "375525753", "domain": "dummy-domain-1753816246.com", "keywords": ["1753816246","dummy-domain-1753816246","simplotel","simplotel 1753816246"]},
    {"name": "Hornbill Farm Retreat- Organic getaway, Functions near Hyderabad", "ga4_id": "500595425", "domain": "hornbillretreat.com", "keywords": ["farm","hornbill","hornbill farm retreat  organic getaway  functions near hyderabad","hornbillretreat","organic","retreat"]},
    {"name": "Hotel Ajanta", "ga4_id": "501053006", "domain": "hotelajanta.com", "keywords": ["ajanta","hotel ajanta","hotelajanta"]},
    {"name": "Sremethila Hotels", "ga4_id": "500133509", "domain": "sremethila.com", "keywords": ["sremethila","sremethila hotels"]},
    {"name": "Mertiya Residency", "ga4_id": "506043072", "domain": "mertiyaresidency.com", "keywords": ["mertiya","mertiya residency","mertiyaresidency","residency"]},
    {"name": "Lawrence Group of Hotels & Resorts", "ga4_id": "517052536", "domain": "lawrencegroup.in", "keywords": ["lawrence","lawrence group of hotels   resorts","lawrencegroup"]},
    {"name": "The Royal Comfort", "ga4_id": "504801428", "domain": "theroyalcomfort.com", "keywords": ["comfort","royal","the royal comfort","theroyalcomfort"]},
    {"name": "Dine at Entartica Seaworld", "ga4_id": "352552304", "domain": "entartica.com", "keywords": ["dine","dine at entartica seaworld","entartica","seaworld"]},
    {"name": "Bhuthanakadu Retreat", "ga4_id": "504169665", "domain": "bhuthanakaduretreat.com", "keywords": ["bhuthanakadu","bhuthanakadu retreat","bhuthanakaduretreat","retreat"]},
    {"name": "Avanya Resorts & Retreat,- old dummy design", "ga4_id": "502893692", "domain": "avanyaresorts4567.com", "keywords": ["avanya","avanya resorts   retreat   old dummy design","avanyaresorts4567","dummy","old","retreat"]},
    {"name": "Ziran Retreat", "ga4_id": "510786679", "domain": "ziranretreat.com", "keywords": ["retreat","ziran","ziran retreat","ziranretreat"]},
    {"name": "Gamyam Retreat (denissonsbeachresort.in) BE Records", "ga4_id": "390907387", "domain": "denissonsbeachresort.com", "keywords": ["denissonsbeachresort","gamyam","gamyam retreat  denissonsbeachresort in  be records","records","retreat"]},
    {"name": "DLS The Classio, Rishikesh 1755588629", "ga4_id": "467575042", "domain": "unknown", "keywords": ["1755588629","classio","dls","dls the classio  rishikesh 1755588629","rishikesh"]},
    {"name": "DLS Hotels The Rock Castle, Shimla 1755588629", "ga4_id": "467575042", "domain": "unknown", "keywords": ["castle","dls","dls hotels the rock castle  shimla 1755588629","rock","shimla"]},
    {"name": "DLS Ganga Bliss, Haridwar 1755588629", "ga4_id": "467575042", "domain": "unknown", "keywords": ["bliss","dls","dls ganga bliss  haridwar 1755588629","ganga","haridwar"]},
    {"name": "DLS Hillcrest Resort, Shimla 1755588629", "ga4_id": "467575042", "domain": "unknown", "keywords": ["1755588629","dls","dls hillcrest resort  shimla 1755588629","hillcrest","shimla"]},
    {"name": "DLS Highland Resort & Spa, Mussoorie 1755588629", "ga4_id": "467575042", "domain": "unknown", "keywords": ["dls","dls highland resort   spa  mussoorie 1755588629","highland","mussoorie","spa"]},
    {"name": "DLS Spring Valley Resort, Dharamshala 1755588629", "ga4_id": "467575042", "domain": "unknown", "keywords": ["dharamshala","dls","dls spring valley resort  dharamshala 1755588629","spring","valley"]},
    {"name": "DLS Grand Luxotica, Dehradun 1755588629", "ga4_id": "467575042", "domain": "unknown", "keywords": ["1755588629","dehradun","dls","dls grand luxotica  dehradun 1755588629","luxotica"]},
    {"name": "DLS Hotel Shiva Sanctuary & Spa, Dharamshala 1755588629", "ga4_id": "467575042", "domain": "unknown", "keywords": ["dls","dls hotel shiva sanctuary   spa  dharamshala 1755588629","sanctuary","shiva","spa"]},
    {"name": "DLS Oak Bush, Mussoorie 1755588629", "ga4_id": "467575042", "domain": "unknown", "keywords": ["bush","dls","dls oak bush  mussoorie 1755588629","mussoorie","oak"]},
    {"name": "DLS Forest Vines Resort & Spa, Ramnagar (Jim Corbett) 1755588629", "ga4_id": "467575042", "domain": "unknown", "keywords": ["dls","dls forest vines resort   spa  ramnagar  jim corbett  1755588629","forest","spa","vines"]},
    {"name": "DLS The Emerald, Nainital 1755588629", "ga4_id": "467575042", "domain": "unknown", "keywords": ["1755588629","dls","dls the emerald  nainital 1755588629","emerald","nainital"]},
    {"name": "DLS Nature Trinket Resort, Dalhousie 1755588629", "ga4_id": "467575042", "domain": "unknown", "keywords": ["dalhousie","dls","dls nature trinket resort  dalhousie 1755588629","nature","trinket"]},
    {"name": "DLS Meghavan Resort, Dharamshala 1755588629", "ga4_id": "467575042", "domain": "unknown", "keywords": ["1755588629","dharamshala","dls","dls meghavan resort  dharamshala 1755588629","meghavan"]},
    {"name": "DLS Divine River Resort & Spa, Rishikesh 1755588629", "ga4_id": "467575042", "domain": "unknown", "keywords": ["divine","dls","dls divine river resort   spa  rishikesh 1755588629","river","spa"]},
    {"name": "DLS Ark Holiday Inn, Dalhousie 1755588629", "ga4_id": "467575042", "domain": "unknown", "keywords": ["ark","dalhousie","dls","dls ark holiday inn  dalhousie 1755588629","holiday"]},
    {"name": "DLS Dalhousie Valley Resort 1755588629", "ga4_id": "467575042", "domain": "unknown", "keywords": ["1755588629","dalhousie","dls","dls dalhousie valley resort 1755588629","valley"]},
    {"name": "DLS Anupam Resort, Dharamshala 1755588629", "ga4_id": "467575042", "domain": "unknown", "keywords": ["1755588629","anupam","dharamshala","dls","dls anupam resort  dharamshala 1755588629"]},
    {"name": "DLS Hotel Devlok, Manali 1755588629", "ga4_id": "467575042", "domain": "unknown", "keywords": ["1755588629","devlok","dls","dls hotel devlok  manali 1755588629","manali"]},
    {"name": "DLS Kapoor Resort, Manali 1755588629", "ga4_id": "467575042", "domain": "unknown", "keywords": ["1755588629","dls","dls kapoor resort  manali 1755588629","kapoor","manali"]},
    {"name": "DLS Park Grace, Haridwar 1755588629", "ga4_id": "467575042", "domain": "unknown", "keywords": ["dls","dls park grace  haridwar 1755588629","grace","haridwar","park"]},
    {"name": "DLS The Pearl, Mussoorie 1755588629", "ga4_id": "467575042", "domain": "unknown", "keywords": ["1755588629","dls","dls the pearl  mussoorie 1755588629","mussoorie","pearl"]},
    {"name": "DLS La Serene Valley, Manali 1755588629", "ga4_id": "467575042", "domain": "unknown", "keywords": ["dls","dls la serene valley  manali 1755588629","manali","serene","valley"]},
    {"name": "DLS MJ River Resort, Rishikesh 1755588629", "ga4_id": "467575042", "domain": "unknown", "keywords": ["1755588629","dls","dls mj river resort  rishikesh 1755588629","rishikesh","river"]},
    {"name": "DLS Whispering Winds, Kasauli 1755588629", "ga4_id": "467575042", "domain": "unknown", "keywords": ["dls","dls whispering winds  kasauli 1755588629","kasauli","whispering","winds"]},
    {"name": "Leopard Hill Resort Bandipur", "ga4_id": "496865000", "domain": "leopardhillbandipur.com", "keywords": ["bandipur","hill","leopard","leopard hill resort bandipur","leopardhillbandipur"]},
    {"name": "Kove Smart Stays, Hyderabad", "ga4_id": "514202745", "domain": "staykove.com", "keywords": ["kove","kove smart stays  hyderabad","smart","staykove","stays"]},
    {"name": "Amer Greens, Bhopal", "ga4_id": "509099099", "domain": "amergreens.com", "keywords": ["amer","amer greens  bhopal","amergreens","bhopal","greens"]},
    {"name": "Anupam Hoteliers", "ga4_id": "500730436", "domain": "anupamhoteliersltd.com", "keywords": ["anupam","anupam hoteliers","anupamhoteliersltd","hoteliers"]},
    {"name": "Ajay Guest House, Paharganj, Delhi (REDIRECTS)", "ga4_id": "386534154", "domain": "ajayguesthouse.com", "keywords": ["ajay","ajay guest house  paharganj  delhi  redirects","ajayguesthouse","guest","house","paharganj"]},
    {"name": "Hotel Aadhar, Gurgaon (REDIRECTS)", "ga4_id": "386467295", "domain": "hotelaadhar.com", "keywords": ["aadhar","gurgaon","hotel aadhar  gurgaon  redirects","hotelaadhar"]},
    {"name": "Le Montfort Munnar", "ga4_id": "470303560", "domain": "lemontfortmunnar.com", "keywords": ["le montfort munnar","lemontfortmunnar","montfort","munnar"]},
    {"name": "Aspen Riverside Resort", "ga4_id": "366937738", "domain": "aspencamp.in", "keywords": ["aspen","aspen riverside resort","aspencamp","riverside"]},
    {"name": "The Fort Unchagaon by Aspen", "ga4_id": "365583394", "domain": "fortunchagaon.com", "keywords": ["aspen","fort","fortunchagaon","the fort unchagaon by aspen","unchagaon"]},
    {"name": "Hotel ORIGIN Hyderabad Airport", "ga4_id": "505840874", "domain": "originhotels.in", "keywords": ["airport","hotel origin hyderabad airport","origin","originhotels"]},
    {"name": "The Enthusiast Hotel Collection", "ga4_id": "503245327", "domain": "enthusiasthotels.com", "keywords": ["collection","enthusiast","enthusiasthotels","the enthusiast hotel collection"]},
    {"name": "Nandan Resort", "ga4_id": "529719672", "domain": "nandanresort.com", "keywords": ["nandan","nandan resort","nandanresort"]},
    {"name": "Surya Plaza", "ga4_id": "504745063", "domain": "suryaplazahotels.com", "keywords": ["plaza","surya","surya plaza","suryaplazahotels"]},
    {"name": "Planet Hotels", "ga4_id": "524307085", "domain": "planethotelsandresorts.com", "keywords": ["planet","planet hotels","planethotelsandresorts"]},
    {"name": "Heritage Village Resorts & Spa 1756790605", "ga4_id": "401519953", "domain": "dummy-domain-1756790605.com", "keywords": ["1756790605","dummy-domain-1756790605","heritage","heritage village resorts   spa 1756790605","spa","village"]},
    {"name": "Teesta Hotels", "ga4_id": "508206205", "domain": "teestahotels.com", "keywords": ["teesta","teesta hotels","teestahotels"]},
    {"name": "Perfectstayz Group", "ga4_id": "512748868", "domain": "perfectstayzgroup.com", "keywords": ["perfectstayz","perfectstayz group","perfectstayzgroup"]},
    {"name": "WOW Hotels & Resorts", "ga4_id": "508952046", "domain": "wowhotelsandresorts.com", "keywords": ["wow","wow hotels   resorts","wowhotelsandresorts"]},
    {"name": "Best Western Premier Westlands (REDIRECT SHELL)", "ga4_id": "390870488", "domain": "bestwesternpluswestlands.com", "keywords": ["best","best western premier westlands  redirect shell","bestwesternpluswestlands","premier","western","westlands"]},
    {"name": "Elysium Studio Suites, Madhapur", "ga4_id": "515001371", "domain": "unknown", "keywords": ["elysium","elysium studio suites  madhapur","madhapur","studio"]},
    {"name": "MYST Resorts, Doddabetta, Ooty", "ga4_id": "516203552", "domain": "mystresorts.com", "keywords": ["doddabetta","myst","myst resorts  doddabetta  ooty","mystresorts","ooty"]},
    {"name": "Ayur On The Beach Nattika", "ga4_id": "510791982", "domain": "thekeralaayurveda.com", "keywords": ["ayur","ayur on the beach nattika","beach","nattika","thekeralaayurveda"]},
    {"name": "Hotel Hukam's Lalit Mahal", "ga4_id": "515880209", "domain": "lalitmahal.in", "keywords": ["hotel hukam s lalit mahal","hukam","lalit","lalitmahal","mahal"]},
    {"name": "The Pinnacle - Electronic City (New Domain)", "ga4_id": "500318829", "domain": "thepinnaclecom.com", "keywords": ["city","electronic","new","pinnacle","the pinnacle   electronic city  new domain","thepinnaclecom"]},
    {"name": "Vinti Resort, Ambaji", "ga4_id": "506633824", "domain": "vintiresort.com", "keywords": ["ambaji","vinti","vinti resort  ambaji","vintiresort"]},
    {"name": "S Hotels, Chennai", "ga4_id": "524646751", "domain": "shotels.in", "keywords": ["s hotels  chennai","shotels"]},
    {"name": "Meraden La Oasis", "ga4_id": "413971081", "domain": "hotelmeradenlaoasis.com", "keywords": ["hotelmeradenlaoasis","meraden","meraden la oasis","oasis"]},
    {"name": "Niche Stays", "ga4_id": "506840341", "domain": "nichestays.com", "keywords": ["niche","niche stays","nichestays","stays"]},
    {"name": "Shakuntalam Hotels", "ga4_id": "516460459", "domain": "shakuntalamhotels.com", "keywords": ["shakuntalam","shakuntalam hotels","shakuntalamhotels"]},
    {"name": "Sunrise Hotels", "ga4_id": "513873199", "domain": "sunrisehotels.in", "keywords": ["sunrise","sunrise hotels","sunrisehotels"]},
    {"name": "Savyasaachii Hotel", "ga4_id": "508535420", "domain": "savyasaachi.com", "keywords": ["savyasaachi","savyasaachii","savyasaachii hotel"]},
    {"name": "A S Hotels, Khajuraho", "ga4_id": "527891740", "domain": "ashotelsandresorts.com", "keywords": ["a s hotels  khajuraho","ashotelsandresorts","khajuraho"]},
    {"name": "Samanvay Luxury Boutique Hotel, Udupi", "ga4_id": "516575920", "domain": "samanvayudupi.com", "keywords": ["boutique","luxury","samanvay","samanvay luxury boutique hotel  udupi","samanvayudupi","udupi"]},
    {"name": "Green Royale Living Spaces", "ga4_id": "516281334", "domain": "greenroyale.in", "keywords": ["green","green royale living spaces","greenroyale","living","royale","spaces"]},
    {"name": "Barefoot at Havelock", "ga4_id": "392146132", "domain": "unknown", "keywords": ["barefoot","barefoot at havelock","havelock"]},
    {"name": "Hotel Natasha Regency", "ga4_id": "510967716", "domain": "natasharegency.com", "keywords": ["hotel natasha regency","natasha","natasharegency","regency"]},
    {"name": "The Evren, Vagator 1760437403", "ga4_id": "494421519", "domain": "dummy-domain-1760437403.com", "keywords": ["1760437403","dummy-domain-1760437403","evren","the evren  vagator 1760437403","vagator"]},
    {"name": "Coorg Orange Blossom Resort & Spa", "ga4_id": "515356175", "domain": "coorgorangeblossomresort.com", "keywords": ["blossom","coorg","coorg orange blossom resort   spa","coorgorangeblossomresort","orange","spa"]},
    {"name": "Hotel Signature Banjara Hills", "ga4_id": "518934652", "domain": "signaturebanjarahills.com", "keywords": ["banjara","hills","hotel signature banjara hills","signature","signaturebanjarahills"]},
    {"name": "Anand Vardhan Resorts - A Spiritual & Wellness Retreat, Manali", "ga4_id": "320597341", "domain": "anandvardhanresorts.com", "keywords": ["anand","anand vardhan resorts   a spiritual   wellness retreat  manali","anandvardhanresorts","spiritual","vardhan","wellness"]},
    {"name": "Vivaana Heritage Hotels", "ga4_id": "513937639", "domain": "vivaana.com", "keywords": ["heritage","vivaana","vivaana heritage hotels"]},
    {"name": "Hotel Durjay Garh", "ga4_id": "497697854", "domain": "hoteldurjaygarh.com", "keywords": ["durjay","garh","hotel durjay garh","hoteldurjaygarh"]},
    {"name": "Rhino & River Wildlife Retreat & Spa, Pobitora", "ga4_id": "524126535", "domain": "rhinoandriver.com", "keywords": ["retreat","rhino","rhino   river wildlife retreat   spa  pobitora","rhinoandriver","river","wildlife"]},
    {"name": "DNC Shevaroys Resorts & Spa, Yercaud", "ga4_id": "530693783", "domain": "dncshevaroys.com", "keywords": ["dnc","dnc shevaroys resorts   spa  yercaud","dncshevaroys","shevaroys","spa","yercaud"]},
    {"name": "HM Suites And Studios", "ga4_id": "513240636", "domain": "hmsuitesandstudios.com", "keywords": ["hm suites and studios","hmsuitesandstudios","studios"]},
    {"name": "Dahabi Hotels", "ga4_id": "510797806", "domain": "dahabihotels.com", "keywords": ["dahabi","dahabi hotels","dahabihotels"]},
    {"name": "Night Hotel Bangkok 1761902645", "ga4_id": "395540853", "domain": "dummy-domain-1761902645.com", "keywords": ["1761902645","bangkok","dummy-domain-1761902645","night","night hotel bangkok 1761902645"]},
    {"name": "Corbett Holiday Forest Resort, Ramnagar", "ga4_id": "518996953", "domain": "holidayforestresort.com", "keywords": ["corbett","corbett holiday forest resort  ramnagar","forest","holiday","holidayforestresort","ramnagar"]},
    {"name": "Sand Heaven", "ga4_id": "525756310", "domain": "hotelsandheaven.com", "keywords": ["heaven","hotelsandheaven","sand","sand heaven"]},
    {"name": "Noor-Us-Sabah Palace", "ga4_id": "522102554", "domain": "noorussabahpalace.com", "keywords": ["noor","noor us sabah palace","noorussabahpalace","sabah"]},
    {"name": "Hotel Vikram", "ga4_id": "517936086", "domain": "hotelvikram.co.in", "keywords": ["hotel vikram","hotelvikram","vikram"]},
    {"name": "Castle Oodeypore", "ga4_id": "474714446", "domain": "castleoodeypore.in", "keywords": ["castle","castle oodeypore","castleoodeypore","oodeypore"]},
    {"name": "Sunrise Hotel", "ga4_id": "515570397", "domain": "hotelsunrise.net", "keywords": ["hotelsunrise","sunrise","sunrise hotel"]},
    {"name": "The Imperial Green", "ga4_id": "516320034", "domain": "theimperialgreen.com", "keywords": ["green","imperial","the imperial green","theimperialgreen"]},
    {"name": "Hotel Silverton", "ga4_id": "514692564", "domain": "hotelsilverton.com", "keywords": ["hotel silverton","hotelsilverton","silverton"]},
    {"name": "Hotel Aurora Bliss, Gachibowli", "ga4_id": "525971863", "domain": "hotelaurorabliss.com", "keywords": ["aurora","bliss","gachibowli","hotel aurora bliss  gachibowli","hotelaurorabliss"]},
    {"name": "Trinetra Inn", "ga4_id": "493638135", "domain": "hoteltrinetrainn.com", "keywords": ["hoteltrinetrainn","trinetra","trinetra inn"]},
    {"name": "Vedic Village Spa Resort, Kolkata (Wellness Packages)", "ga4_id": "501495917", "domain": "thevedicvillage.com", "keywords": ["spa","thevedicvillage","vedic","vedic village spa resort  kolkata  wellness packages","village","wellness"]},
    {"name": "Night Hotel Broadway", "ga4_id": "386971556", "domain": "nighthotelbroadway.com", "keywords": ["broadway","night","night hotel broadway","nighthotelbroadway"]},
    {"name": "Eastlynn Hotels & Resorts", "ga4_id": "520552772", "domain": "eastlynnhotels.com", "keywords": ["eastlynn","eastlynn hotels   resorts","eastlynnhotels"]},
    {"name": "Earthitects", "ga4_id": "517932992", "domain": "earthitects.com", "keywords": ["earthitects"]},
    {"name": "Entartica seaworld, Mayali", "ga4_id": "352552304", "domain": "unknown", "keywords": ["entartica","entartica seaworld  mayali","mayali","seaworld"]},
    {"name": "Entartica seaworld, Bharatpur", "ga4_id": "352552304", "domain": "unknown", "keywords": ["bharatpur","entartica","entartica seaworld  bharatpur","seaworld"]},
    {"name": "The Hotel Prachi, Bhubaneswar", "ga4_id": "516727601", "domain": "prachihotels.com", "keywords": ["bhubaneswar","prachi","prachihotels","the hotel prachi  bhubaneswar"]},
    {"name": "Selene Palm Springs", "ga4_id": "516290914", "domain": "selenepalmsprings.com", "keywords": ["palm","selene","selene palm springs","selenepalmsprings","springs"]},
    {"name": "Monticle Glamps", "ga4_id": "515271348", "domain": "monticleglamps.com", "keywords": ["glamps","monticle","monticle glamps","monticleglamps"]},
    {"name": "Chandys Hotels", "ga4_id": "519641254", "domain": "chandyshotelsandresorts.com", "keywords": ["chandys","chandys hotels","chandyshotelsandresorts"]},
    {"name": "Hotel Polo Towers Group (DNU)", "ga4_id": "418429999", "domain": "hotelpolotowers.co", "keywords": ["hotel polo towers group  dnu","hotelpolotowers","polo","towers"]},
    {"name": "The Bull Boutique Hotel", "ga4_id": "516281419", "domain": "thebullhotels.com", "keywords": ["boutique","bull","the bull boutique hotel","thebullhotels"]},
    {"name": "Eulogia Hotels", "ga4_id": "527358431", "domain": "eulogiahotels.com", "keywords": ["eulogia","eulogia hotels","eulogiahotels"]},
    {"name": "Morya Hotels (REDIRECTS)", "ga4_id": "418197633", "domain": "moryahotels.com", "keywords": ["morya","morya hotels  redirects","moryahotels"]},
    {"name": "Night Hotel Broadway- Do Not Use", "ga4_id": "386971556", "domain": "dummy-domain-1764238889.com", "keywords": ["broadway","dummy-domain-1764238889","night","night hotel broadway  do not use"]},
    {"name": "Polo Hotels and Resorts 1764245990", "ga4_id": "506023095", "domain": "dummy-domain-1764245990.com", "keywords": ["1764245990","dummy-domain-1764245990","polo","polo hotels and resorts 1764245990"]},
    {"name": "Orchid Square Boutique Hotel", "ga4_id": "259305379", "domain": "orchidsquare.in", "keywords": ["boutique","orchid","orchid square boutique hotel","orchidsquare","square"]},
    {"name": "Hatti Eden Coorg", "ga4_id": "461414283", "domain": "hattieden.com", "keywords": ["coorg","eden","hatti","hatti eden coorg","hattieden"]},
    {"name": "Trident The Boutique Hotel, Ooty", "ga4_id": "521712819", "domain": "tridenttheboutiquehotel.com", "keywords": ["boutique","ooty","trident","trident the boutique hotel  ooty","tridenttheboutiquehotel"]},
    {"name": "Kaladwas Lal Haveli", "ga4_id": "517188354", "domain": "kaladwashotels.com", "keywords": ["haveli","kaladwas","kaladwas lal haveli","kaladwashotels","lal"]},
    {"name": "Ram Bhawan Ram Yamuna Prasad Hotel and Resort", "ga4_id": "523119329", "domain": "rbrypresort.com", "keywords": ["bhawan","ram","ram bhawan ram yamuna prasad hotel and resort","rbrypresort","yamuna"]},
    {"name": "Stay Pattern Hotels & Resorts", "ga4_id": "517426908", "domain": "staypattern.com", "keywords": ["pattern","stay","stay pattern hotels   resorts","staypattern"]},
    {"name": "Hotel MN Grand", "ga4_id": "518246876", "domain": "hotelmngrand.com", "keywords": ["hotel mn grand","hotelmngrand"]},
    {"name": "Hotel Kingdom Suites", "ga4_id": "516613488", "domain": "kingdomsuites.in", "keywords": ["hotel kingdom suites","kingdom","kingdomsuites"]},
    {"name": "Apartel by Aarin, Oragadam", "ga4_id": "522892523", "domain": "stayapartel.com", "keywords": ["aarin","apartel","apartel by aarin  oragadam","oragadam","stayapartel"]},
    {"name": "91 Hotels", "ga4_id": "529034482", "domain": "91hotels.in", "keywords": ["91 hotels","91hotels"]},
    {"name": "Karma Lakelands", "ga4_id": "386730458", "domain": "dummy-domain-1765795694.com", "keywords": ["dummy-domain-1765795694","karma","karma lakelands","lakelands"]},
    {"name": "InstaFeel Hotel, Navi Mumbai", "ga4_id": "522379643", "domain": "instafeelhotel.com", "keywords": ["instafeel","instafeel hotel  navi mumbai","instafeelhotel","navi"]},
    {"name": "Anandam Luxury Resorts", "ga4_id": "529888103", "domain": "anandamluxuryresorts.com", "keywords": ["anandam","anandam luxury resorts","anandamluxuryresorts","luxury"]},
    {"name": "Housefinch Residency", "ga4_id": "524569404", "domain": "hotelhousefinchresidency.com", "keywords": ["hotelhousefinchresidency","housefinch","housefinch residency","residency"]},
    {"name": "DLS Hotels Amritsar 200 Steps to The Golden Temple", "ga4_id": "467575042", "domain": "11673_simplotel.com", "keywords": ["11673_simplotel","200","amritsar","dls","dls hotels amritsar 200 steps to the golden temple","steps"]},
    {"name": "Clarks Group of Hotels 1766495335", "ga4_id": "387517650", "domain": "dummy-domain-1766495335.com", "keywords": ["1766495335","clarks","clarks group of hotels 1766495335","dummy-domain-1766495335"]},
    {"name": "Tranquil Cabana Estates & Resort", "ga4_id": "519353324", "domain": "tranquilcabana.in", "keywords": ["cabana","estates","tranquil","tranquil cabana estates   resort","tranquilcabana"]},
    {"name": "Tranquil Diganta Estates & Resort", "ga4_id": "519309052", "domain": "tranquildiganta.com", "keywords": ["diganta","estates","tranquil","tranquil diganta estates   resort","tranquildiganta"]},
    {"name": "Trunk and Trolley", "ga4_id": "517369723", "domain": "trunkandtrolley.com", "keywords": ["trolley","trunk","trunk and trolley","trunkandtrolley"]},
    {"name": "Sands Point Hotel, Pondicherry", "ga4_id": "520561821", "domain": "sandspointhotel.com", "keywords": ["point","pondicherry","sands","sands point hotel  pondicherry","sandspointhotel"]},
    {"name": "Emblem Hotels", "ga4_id": "387014393", "domain": "emblemhotels.in", "keywords": ["emblem","emblem hotels","emblemhotels"]},
    {"name": "Hotel Horizon, Trivandrum", "ga4_id": "524931148", "domain": "thehotelhorizon.com", "keywords": ["horizon","hotel horizon  trivandrum","thehotelhorizon","trivandrum"]},
    {"name": "Fiori Resorts", "ga4_id": "519176435", "domain": "fioriresorts.com", "keywords": ["fiori","fiori resorts","fioriresorts"]},
    {"name": "Hotel Aerostay", "ga4_id": "518915616", "domain": "hotelaerostay.com", "keywords": ["aerostay","hotel aerostay","hotelaerostay"]},
    {"name": "Villa Tanderra", "ga4_id": "521763915", "domain": "villatanderra.com", "keywords": ["tanderra","villa","villa tanderra","villatanderra"]},
    {"name": "Trio Rooms", "ga4_id": "524495812", "domain": "triorooms.com", "keywords": ["rooms","trio","trio rooms","triorooms"]},
    {"name": "Barefoot at Havelock 1767616444", "ga4_id": "392146132", "domain": "11715_simplotel.com", "keywords": ["11715_simplotel","1767616444","barefoot","barefoot at havelock 1767616444","havelock"]},
    {"name": "Barefoot at Havelock", "ga4_id": "392146132", "domain": "unknown", "keywords": ["barefoot","barefoot at havelock","havelock"]},
    {"name": "Karma Lakelands", "ga4_id": "386730458", "domain": "karmalakelands.com", "keywords": ["karma","karma lakelands","karmalakelands","lakelands"]},
    {"name": "Visthara Ventures, Bengaluru", "ga4_id": "525399575", "domain": "vistharaventures.com", "keywords": ["bengaluru","ventures","visthara","visthara ventures  bengaluru","vistharaventures"]},
    {"name": "Emblem Hotel, New Friends Colony, New Delhi- Cloned hotel", "ga4_id": "387014393", "domain": "11726_simplotel.com", "keywords": ["11726_simplotel","colony","emblem","emblem hotel  new friends colony  new delhi  cloned hotel","friends","new"]},
    {"name": "Indus Serenity Retreat, Ladakh", "ga4_id": "524514021", "domain": "indusserenity.com", "keywords": ["indus","indus serenity retreat  ladakh","indusserenity","ladakh","retreat","serenity"]},
    {"name": "SKI - SivaKavi Iconic", "ga4_id": "529020427", "domain": "skiconic.com", "keywords": ["iconic","sivakavi","ski","ski   sivakavi iconic","skiconic"]},
    {"name": "Kohinoor Hotels 1767953164", "ga4_id": "386242336", "domain": "dummy-domain-1767953164.com", "keywords": ["1767953164","dummy-domain-1767953164","kohinoor","kohinoor hotels 1767953164"]},
    {"name": "Marco Polo Hotel, Dubai", "ga4_id": "364788333", "domain": "dummy-domain-1768210543.com", "keywords": ["dubai","dummy-domain-1768210543","marco","marco polo hotel  dubai","polo"]},
    {"name": "SRS Hotels", "ga4_id": "525642163", "domain": "srshotels.co.in", "keywords": ["srs","srs hotels","srshotels"]},
    {"name": "SRS Suites, Koramangala", "ga4_id": "467575042", "domain": "unknown", "keywords": ["koramangala","srs","srs suites  koramangala"]},
    {"name": "BN Tourist Home, Ooty", "ga4_id": "462651681", "domain": "bntouristhome.in", "keywords": ["bn tourist home  ooty","bntouristhome","home","ooty","tourist"]},
    {"name": "Adrushya Estates, Mukteshwar", "ga4_id": "528406621", "domain": "adrushyaestates.com", "keywords": ["adrushya","adrushya estates  mukteshwar","adrushyaestates","estates","mukteshwar"]},
    {"name": "Lindsay Hospitality", "ga4_id": "527821991", "domain": "lindsayhospitality.com", "keywords": ["hospitality","lindsay","lindsay hospitality","lindsayhospitality"]},
    {"name": "Tiki Farms – Polynesian Boutique Resort, Karjat", "ga4_id": "486550390", "domain": "tikifarms.in", "keywords": ["boutique","farms","polynesian","tiki","tiki farms   polynesian boutique resort  karjat","tikifarms"]},
    {"name": "The Jungle Walker Resort", "ga4_id": "518369273", "domain": "thejunglewalker.com", "keywords": ["jungle","the jungle walker resort","thejunglewalker","walker"]},
    {"name": "Grand Iva Hotel, Abha", "ga4_id": "527490992", "domain": "grandivahotelabha.com", "keywords": ["abha","grand iva hotel  abha","grandivahotelabha","iva"]},
    {"name": "Hotel SRS Jade Empire, Bommasandra", "ga4_id": "467575042", "domain": "unknown", "keywords": ["bommasandra","empire","hotel srs jade empire  bommasandra","jade","srs"]},
    {"name": "SRS Vivanta, Kodihalli", "ga4_id": "467575042", "domain": "unknown", "keywords": ["kodihalli","srs","srs vivanta  kodihalli","vivanta"]},
    {"name": "Hotel SRS Manor, Harohalli", "ga4_id": "467575042", "domain": "unknown", "keywords": ["harohalli","hotel srs manor  harohalli","manor","srs"]},
    {"name": "Hotel SRS Elegance, Koramangala", "ga4_id": "467575042", "domain": "unknown", "keywords": ["elegance","hotel srs elegance  koramangala","koramangala","srs"]},
    {"name": "The Golden Tusk - DEMO (DNU)", "ga4_id": "468442679", "domain": "11794_simplotel.com", "keywords": ["11794_simplotel","demo","golden","the golden tusk   demo  dnu","tusk"]},
    {"name": "The Golden Tusk, Jim Corbett", "ga4_id": "364992257", "domain": "11799_simplotel.com", "keywords": ["11799_simplotel","corbett","golden","jim","the golden tusk  jim corbett","tusk"]},
    {"name": "The Oasis Hotel Vadodara", "ga4_id": "458035551", "domain": "theoasishotel.net", "keywords": ["oasis","the oasis hotel vadodara","theoasishotel","vadodara"]},
    {"name": "Villa the Retreat", "ga4_id": "528057830", "domain": "kazirangavillatheretreat.com", "keywords": ["kazirangavillatheretreat","retreat","villa","villa the retreat"]},
    {"name": "BN Tourist Home, Ooty 1770039289", "ga4_id": "466985469", "domain": "unknown", "keywords": ["1770039289","bn tourist home  ooty 1770039289","home","ooty","tourist"]},
    {"name": "ELYSIUM Premier Suites Hitech City", "ga4_id": "515001371", "domain": "unknown", "keywords": ["city","elysium","elysium premier suites hitech city","hitech","premier"]},
    {"name": "Elysium Hotels", "ga4_id": "515001371", "domain": "elysiumsuites.in", "keywords": ["elysium","elysium hotels","elysiumsuites"]},
    {"name": "Elysium Studio Suites, Madhapur - Dummy Shell for refrence", "ga4_id": "515001371", "domain": "11834_simplotel.com", "keywords": ["11834_simplotel","dummy","elysium","elysium studio suites  madhapur   dummy shell for refrence","madhapur","studio"]},
    {"name": "Tripanyday", "ga4_id": "528594945", "domain": "tripanyday.com", "keywords": ["tripanyday"]},
    {"name": "Apartel by Aarin, Oragadam", "ga4_id": "522892523", "domain": "unknown", "keywords": ["aarin","apartel","apartel by aarin  oragadam","oragadam"]},
    {"name": "Urban Comforts", "ga4_id": "527828571", "domain": "urbancomforts.in", "keywords": ["comforts","urban","urban comforts","urbancomforts"]},
    {"name": "The Almanac", "ga4_id": "494318107", "domain": "thealmanac.in", "keywords": ["almanac","the almanac","thealmanac"]},
    {"name": "Brio Hotel, Kolkata", "ga4_id": "511716155", "domain": "briohotels.com", "keywords": ["brio","brio hotel  kolkata","briohotels"]},
    {"name": "Casa Hotel Madhapur", "ga4_id": "500139974", "domain": "casahotelmadhapur.com", "keywords": ["casa","casa hotel madhapur","casahotelmadhapur","madhapur"]},
    {"name": "Springs Hotel & Spa, J.C. Road - DNU", "ga4_id": "385225792", "domain": "11875_simplotel.com", "keywords": ["11875_simplotel","road","spa","springs","springs hotel   spa  j c  road   dnu"]},
    {"name": "The Lavender Hotel", "ga4_id": "528769818", "domain": "thelavenderhotel.com", "keywords": ["lavender","the lavender hotel","thelavenderhotel"]},
    {"name": "Coorg Jungle Camp Backwater Resort, Kushalnagar", "ga4_id": "520292971", "domain": "unknown", "keywords": ["backwater","camp","coorg","coorg jungle camp backwater resort  kushalnagar","jungle"]},
    {"name": "Sands Point Hotel Back up", "ga4_id": "520561821", "domain": "dummy-domain-1772085466.com", "keywords": ["back","dummy-domain-1772085466","point","sands","sands point hotel back up"]},
    {"name": "Parampara Resort & Spa, Kushalnagar", "ga4_id": "386683555", "domain": "unknown", "keywords": ["kushalnagar","parampara","parampara resort   spa  kushalnagar","spa"]},
    {"name": "The Residency Group of Hotels 1772459347", "ga4_id": "386927028", "domain": "dummy-domain-1772459347.com", "keywords": ["1772459347","dummy-domain-1772459347","residency","the residency group of hotels 1772459347"]},
    {"name": "Ilara Hotels & Spa -RE_MAP", "ga4_id": "500756098", "domain": "dummy-domain-1772522033.com", "keywords": ["dummy-domain-1772522033","ilara","ilara hotels   spa  re_map","re_map","spa"]},
    {"name": "Confirm Inn", "ga4_id": "529846265", "domain": "confirminnkota.com", "keywords": ["confirm","confirm inn","confirminnkota"]},
    {"name": "Springs Hotel & Spa, Bangalore (REDIRECT)", "ga4_id": "385225792", "domain": "springshotels.co", "keywords": ["spa","springs","springs hotel   spa  bangalore  redirect","springshotels"]},
    {"name": "RD's Nature Retreat, Bangalore (Day Out)", "ga4_id": "313218246", "domain": "rdsnatureretreat.com", "keywords": ["day","nature","out","rd s nature retreat  bangalore  day out","rdsnatureretreat","retreat"]},
    {"name": "Red Earth Kabini", "ga4_id": "528127307", "domain": "redearth.in", "keywords": ["earth","kabini","red","red earth kabini","redearth"]},
    {"name": "Hotel Polo Towers Group (REDIRECTS)", "ga4_id": "418429999", "domain": "hotelpolotowers.com", "keywords": ["hotel polo towers group  redirects","hotelpolotowers","polo","towers"]},
    {"name": "3102bce - A Vedic Resort by Lindsay (REDIRECTS)", "ga4_id": "387184944", "domain": "3102bce.com", "keywords": ["3102bce","3102bce   a vedic resort by lindsay  redirects","lindsay","vedic"]},
    {"name": "Lindsay Manor (REDIRECTS)", "ga4_id": "444092794", "domain": "lindsay-manor.com", "keywords": ["lindsay","lindsay manor  redirects","lindsay-manor","manor"]},
    {"name": "The Lindsay (REDIRECTS)", "ga4_id": "390901629", "domain": "thelindsay.in", "keywords": ["lindsay","the lindsay  redirects","thelindsay"]},
    {"name": "Tadoba Tiger Valley Resort", "ga4_id": "530157574", "domain": "tadobatigervalleyresort.com", "keywords": ["tadoba","tadoba tiger valley resort","tadobatigervalleyresort","tiger","valley"]},
    {"name": "Hotel City Inn, Varanasi - Redirects", "ga4_id": "421321536", "domain": "hotelcityinn.org", "keywords": ["city","hotel city inn  varanasi   redirects","hotelcityinn","varanasi"]},
    {"name": "Jenneys Residency, Coimbatore 1773668235", "ga4_id": "386226345", "domain": "dummy-domain-1773668235.com", "keywords": ["1773668235","coimbatore","dummy-domain-1773668235","jenneys","jenneys residency  coimbatore 1773668235","residency"]},
    {"name": "Darza Resorts Wedding page", "ga4_id": "472460360", "domain": "dummy-domain-1774000499.com", "keywords": ["darza","darza resorts wedding page","dummy-domain-1774000499","page","wedding"]},
    {"name": "The Saisa Resort, Solapur", "ga4_id": "529928907", "domain": "saisaresort.com", "keywords": ["saisa","saisaresort","solapur","the saisa resort  solapur"]},
    {"name": "GRT Hotels & Resorts 1774864963", "ga4_id": "464163304", "domain": "dummy-domain-1774864963.com", "keywords": ["1774864963","dummy-domain-1774864963","grt","grt hotels   resorts 1774864963"]},
]

# Active property — overridden by sidebar selection
PROPERTY_ID = PORTFOLIO[0]["ga4_id"]
SITE_URL    = ""
SCOPES = [
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/webmasters.readonly"
]

MONTH_LABELS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
YEAR_COLORS  = ["#4C8BF5","#34A853","#FBBC04","#EA4335","#9C27B0"]
SEGMENT_COLORS = {
    "Direct":         "#4C8BF5",
    "Paid Search":    "#EA4335",
    "Paid Social":    "#FBBC04",
    "Organic Social": "#34A853",
    "Referral":       "#9C27B0",
    "Email":          "#00BCD4",
    "Display":        "#FF5722",
    "Unassigned":     "#9E9E9E",
    "Cross-network":  "#795548",
}

# ── AUTH ──────────────────────────────────────────────────────────────────────
def get_credentials():
    """
    Returns Google credentials using service account.
    Priority:
      1. Streamlit Cloud — reads service account JSON from st.secrets
      2. Local — reads from service account JSON file on disk
    Never expires. No browser login required.
    """
    import json

    sa_scopes = [
        "https://www.googleapis.com/auth/analytics.readonly",
        "https://www.googleapis.com/auth/webmasters.readonly",
    ]

    # ── Streamlit Cloud: load from secrets ───────────────────────────────────
    try:
        if hasattr(st, "secrets") and "service_account_json" in st.secrets:
            sa_info = json.loads(st.secrets["service_account_json"])
            return service_account.Credentials.from_service_account_info(
                sa_info, scopes=sa_scopes
            )
    except Exception:
        pass  # No secrets.toml locally — fall through to file-based auth

    # ── Local: load from service account JSON file ───────────────────────────
    sa_file = "cs-analytics-link-b5e07310a9fe.json"
    if os.path.exists(sa_file):
        return service_account.Credentials.from_service_account_file(
            sa_file, scopes=sa_scopes
        )

    # ── Fallback: original OAuth flow (local dev without service account) ────
    creds = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.pickle", "wb") as f:
            pickle.dump(creds, f)
    return creds


def get_fallback_credentials_list():
    """
    Returns a list of SECONDARY and TERTIARY service account credentials.
    Used when the primary service account hits Google's accounts-per-user limit.
    """
    sa_scopes = [
        "https://www.googleapis.com/auth/analytics.readonly",
        "https://www.googleapis.com/auth/webmasters.readonly",
    ]
    fallbacks = []
    # Secondary service account (simplotel-dashboard-2)
    try:
        if hasattr(st, "secrets") and "service_account_json_2" in st.secrets:
            sa_info = json.loads(st.secrets["service_account_json_2"])
            fallbacks.append(service_account.Credentials.from_service_account_info(sa_info, scopes=sa_scopes))
    except Exception:
        pass
    if not any("dashboard-2" in str(getattr(c, "service_account_email", "")) for c in fallbacks):
        sa2 = "cs-analytics-link-18eabe49b35f.json"
        if os.path.exists(sa2):
            try: fallbacks.append(service_account.Credentials.from_service_account_file(sa2, scopes=sa_scopes))
            except Exception: pass
    # Tertiary service account (simplotel-dashboard-3)
    try:
        if hasattr(st, "secrets") and "service_account_json_3" in st.secrets:
            sa_info = json.loads(st.secrets["service_account_json_3"])
            fallbacks.append(service_account.Credentials.from_service_account_info(sa_info, scopes=sa_scopes))
    except Exception:
        pass
    if not any("dashboard-3" in str(getattr(c, "service_account_email", "")) for c in fallbacks):
        sa3 = "cs-analytics-link-dbdb3e9e2df8.json"
        if os.path.exists(sa3):
            try: fallbacks.append(service_account.Credentials.from_service_account_file(sa3, scopes=sa_scopes))
            except Exception: pass
    return fallbacks

def _run_ga4_report(req):
    """Run a GA4 report. On PermissionDenied, try each fallback service account."""
    creds  = get_credentials()
    client = BetaAnalyticsDataClient(credentials=creds)
    try:
        return client.run_report(req)
    except Exception as e:
        if _check_permission_error(e):
            for fb in get_fallback_credentials_list():
                try: return BetaAnalyticsDataClient(credentials=fb).run_report(req)
                except Exception: continue
            return None
        raise

def _run_gsc_query(site_url, body):
    """Run a GSC query. On PermissionDenied, try each fallback service account."""
    creds   = get_credentials()
    service = build("searchconsole", "v1", credentials=creds)
    try:
        return service.searchanalytics().query(siteUrl=site_url, body=body).execute()
    except Exception as e:
        if _check_permission_error(e):
            for fb in get_fallback_credentials_list():
                try:
                    s2 = build("searchconsole", "v1", credentials=fb)
                    return s2.searchanalytics().query(siteUrl=site_url, body=body).execute()
                except Exception: continue
            return None
        raise

# ── DATA FUNCTIONS ────────────────────────────────────────────────────────────
# Permission error flag — set True when service account lacks access to property
_GA4_PERMISSION_ERROR = False
_GA4_PERMISSION_MSG   = ""

def _check_permission_error(e):
    """Return True if this is a GA4/GSC PermissionDenied error."""
    err = str(e).lower()
    return "permissiondenied" in err or "permission denied" in err or "403" in err
def get_ga4_data(start, end):
    req = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=str(start), end_date=str(end))],
        dimensions=[Dimension(name="sessionDefaultChannelGroup")],
        metrics=[Metric(name="sessions"), Metric(name="engagementRate"), Metric(name="bounceRate")]
    )
    resp = _run_ga4_report(req)
    if resp is None:
        global _GA4_PERMISSION_ERROR, _GA4_PERMISSION_MSG
        _GA4_PERMISSION_ERROR = True
        _GA4_PERMISSION_MSG   = str(PROPERTY_ID)
        return pd.DataFrame()
    rows = []
    for row in resp.rows:
        rows.append({
            "channel":    row.dimension_values[0].value,
            "sessions":   int(row.metric_values[0].value),
            "engagement": round(float(row.metric_values[1].value) * 100, 1),
            "bounce":     round(float(row.metric_values[2].value) * 100, 1),
        })
    return pd.DataFrame(rows).sort_values("sessions", ascending=False)

def get_ga4_monthly_yoy():
    req = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date="2022-01-01", end_date="today")],
        dimensions=[Dimension(name="year"), Dimension(name="month")],
        metrics=[Metric(name="sessions")]
    )
    resp = _run_ga4_report(req)
    if resp is None:
        global _GA4_PERMISSION_ERROR, _GA4_PERMISSION_MSG
        _GA4_PERMISSION_ERROR = True
        _GA4_PERMISSION_MSG   = str(PROPERTY_ID)
        return pd.DataFrame()
    rows = []
    for row in resp.rows:
        rows.append({
            "year":     int(row.dimension_values[0].value),
            "month":    int(row.dimension_values[1].value),
            "sessions": int(row.metric_values[0].value),
        })
    return pd.DataFrame(rows)

def get_ga4_monthly_yoy_organic():
    req = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date="2022-01-01", end_date="today")],
        dimensions=[Dimension(name="year"), Dimension(name="month"), Dimension(name="sessionDefaultChannelGroup")],
        metrics=[Metric(name="sessions")]
    )
    resp = _run_ga4_report(req)
    if resp is None:
        global _GA4_PERMISSION_ERROR, _GA4_PERMISSION_MSG
        _GA4_PERMISSION_ERROR = True
        _GA4_PERMISSION_MSG   = str(PROPERTY_ID)
        return pd.DataFrame()
    rows = []
    for row in resp.rows:
        if row.dimension_values[2].value == "Organic Search":
            rows.append({
                "year":     int(row.dimension_values[0].value),
                "month":    int(row.dimension_values[1].value),
                "sessions": int(row.metric_values[0].value),
            })
    return pd.DataFrame(rows)

def get_ga4_segmentation_monthly():
    seg_end   = date.today() - timedelta(days=1)
    seg_start = seg_end.replace(day=1) - timedelta(days=365 * 2)
    req = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=str(seg_start), end_date=str(seg_end))],
        dimensions=[Dimension(name="year"), Dimension(name="month"), Dimension(name="sessionDefaultChannelGroup")],
        metrics=[Metric(name="sessions")]
    )
    resp = _run_ga4_report(req)
    if resp is None:
        global _GA4_PERMISSION_ERROR, _GA4_PERMISSION_MSG
        _GA4_PERMISSION_ERROR = True
        _GA4_PERMISSION_MSG   = str(PROPERTY_ID)
        return pd.DataFrame()
    rows = []
    for row in resp.rows:
        channel = row.dimension_values[2].value
        if channel != "Organic Search":
            rows.append({
                "year":     int(row.dimension_values[0].value),
                "month":    int(row.dimension_values[1].value),
                "channel":  channel,
                "sessions": int(row.metric_values[0].value),
            })
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df["month_label"] = df.apply(
        lambda r: f"{MONTH_LABELS[int(r['month'])-1]} '{str(int(r['year']))[2:]}", axis=1
    )
    df["sort_key"] = df["year"] * 100 + df["month"]
    return df.sort_values("sort_key")

def get_ga4_monthly_engagement(start, end):
    req = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=str(start), end_date=str(end))],
        dimensions=[Dimension(name="year"), Dimension(name="month")],
        metrics=[Metric(name="engagementRate")],
        dimension_filter=FilterExpression(
            filter=Filter(
                field_name="sessionDefaultChannelGroup",
                string_filter=Filter.StringFilter(value="Organic Search")
            )
        ),
    )
    resp = _run_ga4_report(req)
    if resp is None:
        global _GA4_PERMISSION_ERROR, _GA4_PERMISSION_MSG
        _GA4_PERMISSION_ERROR = True
        _GA4_PERMISSION_MSG   = str(PROPERTY_ID)
        return pd.DataFrame()
    rows = []
    for row in resp.rows:
        rows.append({
            "year":            int(row.dimension_values[0].value),
            "month":           int(row.dimension_values[1].value),
            "engagement_rate": round(float(row.metric_values[0].value) * 100, 1),
        })
    df = pd.DataFrame(rows).sort_values(["year", "month"])
    df["label"] = df.apply(lambda r: f"{MONTH_LABELS[int(r['month'])-1]} {int(r['year'])}", axis=1)
    return df

def get_ga4_device(start, end):
    req = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=str(start), end_date=str(end))],
        dimensions=[Dimension(name="deviceCategory")],
        metrics=[Metric(name="sessions"), Metric(name="engagementRate"), Metric(name="averageSessionDuration")]
    )
    resp = _run_ga4_report(req)
    if resp is None:
        global _GA4_PERMISSION_ERROR, _GA4_PERMISSION_MSG
        _GA4_PERMISSION_ERROR = True
        _GA4_PERMISSION_MSG   = str(PROPERTY_ID)
        return pd.DataFrame()
    rows = []
    for row in resp.rows:
        rows.append({
            "Device":                            row.dimension_values[0].value.title(),
            "Sessions":                          int(row.metric_values[0].value),
            "Engagement Rate (%)":               round(float(row.metric_values[1].value) * 100, 1),
            "Average Engagement Time (seconds)": round(float(row.metric_values[2].value), 1),
        })
    return pd.DataFrame(rows).sort_values("Sessions", ascending=False)

def get_ga4_top_cities():
    start  = date.today() - timedelta(days=180)
    req = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=str(start), end_date="today")],
        dimensions=[Dimension(name="city")],
        metrics=[Metric(name="sessions")],
        dimension_filter=FilterExpression(
            filter=Filter(
                field_name="sessionDefaultChannelGroup",
                string_filter=Filter.StringFilter(value="Organic Search")
            )
        ),
        limit=12,
        order_bys=[{"metric": {"metric_name": "sessions"}, "desc": True}]
    )
    resp = _run_ga4_report(req)
    if resp is None:
        global _GA4_PERMISSION_ERROR, _GA4_PERMISSION_MSG
        _GA4_PERMISSION_ERROR = True
        _GA4_PERMISSION_MSG   = str(PROPERTY_ID)
        return pd.DataFrame()
    rows = []
    for row in resp.rows:
        city = row.dimension_values[0].value
        if city not in ("(not set)", ""):
            rows.append({"City": city, "Sessions": int(row.metric_values[0].value)})
    return pd.DataFrame(rows).head(10)

def get_ga4_top_countries():
    start  = date.today() - timedelta(days=180)
    req = RunReportRequest(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=str(start), end_date="today")],
        dimensions=[Dimension(name="country")],
        metrics=[Metric(name="sessions")],
        dimension_filter=FilterExpression(
            filter=Filter(
                field_name="sessionDefaultChannelGroup",
                string_filter=Filter.StringFilter(value="Organic Search")
            )
        ),
        limit=10,
        order_bys=[{"metric": {"metric_name": "sessions"}, "desc": True}]
    )
    resp = _run_ga4_report(req)
    if resp is None:
        global _GA4_PERMISSION_ERROR, _GA4_PERMISSION_MSG
        _GA4_PERMISSION_ERROR = True
        _GA4_PERMISSION_MSG   = str(PROPERTY_ID)
        return pd.DataFrame()
    rows = []
    for row in resp.rows:
        rows.append({"Country": row.dimension_values[0].value, "Sessions": int(row.metric_values[0].value)})
    return pd.DataFrame(rows).head(10)

def get_gsc_data(start, end):
    body = {
        "startDate":  str(start),
        "endDate":    str(end),
        "dimensions": ["query"],
        "rowLimit":   25,
        "orderBy":    [{"fieldName": "clicks", "sortOrder": "DESCENDING"}]
    }
    resp = _run_gsc_query(SITE_URL, body)
    if resp is None:
        return pd.DataFrame()
    rows = []
    for row in resp.get("rows", []):
        rows.append({
            "Keyword":     row["keys"][0],
            "Clicks":      int(row["clicks"]),
            "Impressions": int(row["impressions"]),
            "CTR (%)":     round(row["ctr"] * 100, 1),
            "Position":    round(row["position"], 1),
        })
    return pd.DataFrame(rows)

def is_brand(keyword):
    kw = keyword.lower()
    return any(b in kw for b in BRAND_KEYWORDS)

def get_gsc_brand_nonbrand(start, end):
    creds   = get_credentials()
    service = build("searchconsole", "v1", credentials=creds)
    body = {
        "startDate":  str(start),
        "endDate":    str(end),
        "dimensions": ["date", "query"],
        "rowLimit":   25000,
    }
    resp = service.searchanalytics().query(siteUrl=SITE_URL, body=body).execute()
    rows = []
    for row in resp.get("rows", []):
        rows.append({
            "date":        row["keys"][0],
            "query":       row["keys"][1],
            "clicks":      int(row["clicks"]),
            "impressions": int(row["impressions"]),
            "ctr":         round(row["ctr"] * 100, 2),
        })
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()
    df["date"]     = pd.to_datetime(df["date"])
    df["month"]    = df["date"].dt.to_period("M")
    df["is_brand"] = df["query"].apply(is_brand)
    brand    = df[df["is_brand"]].groupby("month").agg({"clicks": "sum", "impressions": "sum", "ctr": "mean"}).reset_index()
    nonbrand = df[~df["is_brand"]].groupby("month").agg({"clicks": "sum", "impressions": "sum", "ctr": "mean"}).reset_index()
    brand["ctr"]    = brand["ctr"].round(2)
    nonbrand["ctr"] = nonbrand["ctr"].round(2)
    return brand, nonbrand

# ── CHART HELPERS ─────────────────────────────────────────────────────────────

# Shared base layout for all charts — presentation-ready defaults
BASE = dict(
    plot_bgcolor="white",
    paper_bgcolor="white",
    font=dict(family="Arial", size=13),
)

def yoy_layout(y_title):
    """Layout for all YOY grouped bar charts."""
    return dict(
        **BASE,
        barmode="group", bargap=0.15, bargroupgap=0.05,
        yaxis=dict(title=y_title, gridcolor="#eeeeee", tickformat=",", rangemode="tozero", title_font=dict(size=13)),
        xaxis=dict(title="", tickfont=dict(size=12)),
        legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="center", x=0.5, font=dict(size=12)),
        # Extra top + right margin: top for legend, right so outside labels aren't clipped
        margin=dict(t=80, b=60, l=70, r=40),
        height=460,
    )

def horiz_bar_layout(x_title, max_val):
    """Layout for horizontal bar charts — right margin scales with the largest label."""
    # Each digit in the label ~ 8px, plus padding
    label_width = max(len(f"{max_val:,}") * 9 + 30, 80)
    return dict(
        **BASE,
        xaxis=dict(
            title=x_title, gridcolor="#eeeeee", tickformat=",",
            title_font=dict(size=13), tickfont=dict(size=12),
            # Extend range so outside labels have room
            range=[0, max_val * 1.35],
        ),
        yaxis=dict(autorange="reversed", tickfont=dict(size=12)),
        margin=dict(t=30, b=60, l=160, r=label_width),
        height=420,
    )

def gsc_clean_chart(df_curr, df_prev, this_year, last_year, title, color_curr, color_prev):
    """Two-panel chart: Clicks + CTR line (top), Impressions (bottom). Fully labelled."""
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        row_heights=[0.55, 0.45],
        vertical_spacing=0.10,
        specs=[[{"secondary_y": True}], [{"secondary_y": False}]],
        subplot_titles=["Clicks & Click-Through Rate (%)", "Impressions"]
    )
    import datetime as _dt
    def _fmt(s):
        try:
            return _dt.datetime.strptime(str(s), "%Y-%m").strftime("%b %Y")
        except Exception:
            return str(s)

    for df, yr, color, dash in [
        (df_prev, last_year, color_prev, "dot"),
        (df_curr, this_year, color_curr, "solid"),
    ]:
        if df is not None and not df.empty:
            labels = [_fmt(m) for m in df["month"].astype(str).tolist()]
            fig.add_trace(go.Bar(
                name=f"Clicks {yr}", x=labels, y=df["clicks"],
                marker_color=color, legendgroup=yr,
                text=[f"{v:,}" for v in df["clicks"]],
                textposition="outside", textfont=dict(size=10),
                cliponaxis=False,
            ), row=1, col=1, secondary_y=False)
            fig.add_trace(go.Scatter(
                name=f"CTR {yr} (%)", x=labels, y=df["ctr"],
                mode="lines+markers",
                line=dict(color=color, width=2, dash=dash),
                marker=dict(size=5), legendgroup=yr,
            ), row=1, col=1, secondary_y=True)
            fig.add_trace(go.Bar(
                name=f"Impressions {yr}", x=labels, y=df["impressions"],
                marker_color=color, legendgroup=yr, showlegend=False,
                text=[f"{v:,}" for v in df["impressions"]],
                textposition="outside", textfont=dict(size=10),
                cliponaxis=False,
            ), row=2, col=1)

    # Build full sorted label list (already formatted as "Jan 2025" etc)
    all_fmt_labels = sorted(set(
        ([_fmt(m) for m in df_curr["month"].astype(str).tolist()] if df_curr is not None and not df_curr.empty else []) +
        ([_fmt(m) for m in df_prev["month"].astype(str).tolist()] if df_prev is not None and not df_prev.empty else [])
    ), key=lambda s: _dt.datetime.strptime(s, "%b %Y"))

    fig.update_layout(
        title=dict(text=title, font=dict(size=15, family="Arial")),
        barmode="group",
        **BASE,
        legend=dict(orientation="h", yanchor="bottom", y=1.06, xanchor="center", x=0.5, font=dict(size=11)),
        margin=dict(t=120, b=110, l=70, r=70),
        height=640,
    )
    # Force every month label on the shared x-axis
    fig.update_xaxes(
        tickmode="array",
        tickvals=all_fmt_labels,
        ticktext=all_fmt_labels,
        tickangle=-45,
        tickfont=dict(size=11),
        row=2, col=1,
    )
    fig.update_yaxes(title_text="Clicks", gridcolor="#eeeeee", tickformat=",",
                     title_font=dict(size=12), row=1, col=1, secondary_y=False)
    fig.update_yaxes(title_text="CTR (%)", showgrid=False,
                     title_font=dict(size=12), row=1, col=1, secondary_y=True)
    fig.update_yaxes(title_text="Impressions", gridcolor="#eeeeee", tickformat=",",
                     title_font=dict(size=12), row=2, col=1)
    return fig

# ── PROPERTY AUTO-DISCOVERY ──────────────────────────────────────────────────
from difflib import SequenceMatcher

@st.cache_data(ttl=3600, show_spinner=False)
def discover_properties():
    """
    Build PROPERTIES dict from PORTFOLIO registry.
    GSC URL is auto-matched from the verified sites list using the known domain.
    Returns dict keyed by property name for use in sidebar.
    """
    creds = get_credentials()

    # ── GSC: fetch all verified sites ────────────────────────────────────────
    gsc_sites = []
    try:
        gsc_service = build("searchconsole", "v1", credentials=creds)
        resp = gsc_service.sites().list().execute()
        gsc_sites = [s["siteUrl"] for s in resp.get("siteEntry", [])]
    except Exception:
        gsc_sites = []

    def clean_domain(url):
        return (url.replace("sc-domain:", "")
                   .replace("https://", "").replace("http://", "")
                   .replace("www.", "").rstrip("/").lower())

    def find_gsc_url(domain):
        """Find the GSC site URL that matches the given domain."""
        for site in gsc_sites:
            if domain in clean_domain(site) or clean_domain(site) in domain:
                return site
        return ""

    # ── Build PROPERTIES from registry ───────────────────────────────────────
    properties = {}
    for prop in PORTFOLIO:
        gsc_url = find_gsc_url(prop["domain"])
        properties[prop["name"]] = {
            "ga4_id":   prop["ga4_id"],
            "gsc_url":  gsc_url,
            "domain":   prop["domain"],
            "name":     prop["name"],
            "keywords": prop["keywords"],
        }
    return properties

def fuzzy_filter(query, properties):
    """Return property labels sorted by fuzzy match score to query."""
    if not query.strip():
        return list(properties.keys())
    q = query.lower().strip()
    scores = []
    for label, meta in properties.items():
        candidates = [
            label,
            meta.get("name", ""),
            meta.get("domain", ""),
            meta.get("ga4_id", ""),
        ]
        best = 0
        for c in candidates:
            c = c.lower()
            if q in c:
                best = 100
                break
            s = SequenceMatcher(None, q, c).ratio() * 100
            if s > best:
                best = s
        scores.append((label, best))
    scores.sort(key=lambda x: x[1], reverse=True)
    filtered = [lbl for lbl, sc in scores if sc > 30]
    return filtered if filtered else [scores[0][0]]

# ── SIDEBAR ───────────────────────────────────────────────────────────────────
st.sidebar.title("Simplotel")
st.sidebar.markdown("**Select Property**")

# Auto-discover properties (cached for 1 hour)
with st.sidebar:
    with st.spinner("Loading properties..."):
        PROPERTIES = discover_properties()

if not PROPERTIES:
    st.sidebar.error("No portfolio properties found. Check credentials and PORTFOLIO_GA4_IDS.")
    st.stop()

# Search bar — fuzzy filtering
search_query = st.sidebar.text_input(
    "Search property",
    placeholder="Type name, domain, or GA4 ID...",
    label_visibility="collapsed",
)

matched = fuzzy_filter(search_query, PROPERTIES)

selected_label = st.sidebar.selectbox(
    "Property",
    options=matched,
    label_visibility="collapsed",
)

# Set active property config from discovered data
PROPERTY_ID    = PROPERTIES[selected_label]["ga4_id"]
SITE_URL       = PROPERTIES[selected_label]["gsc_url"]
BRAND_KEYWORDS = PROPERTIES[selected_label].get("keywords", [])

gsc_available = bool(SITE_URL)
st.sidebar.caption(f"GA4 ID: {PROPERTY_ID}")
if gsc_available:
    st.sidebar.caption(f"GSC: {SITE_URL}")
else:
    st.sidebar.caption("GSC: not matched — check domain")

st.sidebar.markdown("---")

# ── DATE PICKER — DROPDOWN STYLE ──────────────────────────────────────────────
import calendar as _cal

_cal_today = date.today()
today      = _cal_today

# Session state init
for _k, _v in [
    ("dp_open",       False),
    ("dp_year",       _cal_today.year),
    ("dp_month",      _cal_today.month),
    ("dp_start",      _cal_today - timedelta(days=29)),
    ("dp_end",        _cal_today - timedelta(days=1)),
    ("dp_tmp_start",  None),
    ("dp_tmp_end",    None),
    ("dp_step",       "start"),
    ("dp_preset",     "Last 30 days"),
]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ── Dropdown trigger button ────────────────────────────────────────────────────
_s  = st.session_state["dp_start"]
_e  = st.session_state["dp_end"]
_trigger_label = (
    f"{st.session_state['dp_preset']}  ·  "
    f"{_s.strftime('%b %d')} – {_e.strftime('%b %d, %Y')}  ▾"
)
if st.sidebar.button(_trigger_label, key="dp_trigger", use_container_width=True):
    st.session_state["dp_open"]      = not st.session_state["dp_open"]
    st.session_state["dp_tmp_start"] = st.session_state["dp_start"]
    st.session_state["dp_tmp_end"]   = st.session_state["dp_end"]
    st.session_state["dp_step"]      = "start"
    st.rerun()

# ── Dropdown panel (shown when open) ──────────────────────────────────────────
if st.session_state["dp_open"]:

    _cy  = st.session_state["dp_year"]
    _cm  = st.session_state["dp_month"]
    _ts  = st.session_state["dp_tmp_start"]
    _te  = st.session_state["dp_tmp_end"]

    # Start / End date text inputs at top
    _di1, _di2 = st.sidebar.columns(2)
    with _di1:
        _new_start = st.date_input(
            "Start date",
            value=_ts if _ts else _cal_today - timedelta(days=29),
            key="dp_inp_start"
        )
        if _new_start != _ts:
            st.session_state["dp_tmp_start"] = _new_start
            if _new_start > (_te or _new_start):
                st.session_state["dp_tmp_end"] = _new_start
            st.rerun()
    with _di2:
        _new_end = st.date_input(
            "End date",
            value=_te if _te else _cal_today - timedelta(days=1),
            key="dp_inp_end"
        )
        if _new_end != _te:
            st.session_state["dp_tmp_end"] = _new_end
            st.rerun()


    # Apply / Cancel
    _ac1, _ac2 = st.sidebar.columns(2)
    with _ac1:
        if st.button("Cancel", key="dp_cancel", use_container_width=True):
            st.session_state["dp_open"] = False
            st.rerun()
    with _ac2:
        if st.button("Apply", key="dp_apply", use_container_width=True, type="primary"):
            if st.session_state["dp_tmp_start"] and st.session_state["dp_tmp_end"]:
                st.session_state["dp_start"]  = st.session_state["dp_tmp_start"]
                st.session_state["dp_end"]    = st.session_state["dp_tmp_end"]
                st.session_state["dp_preset"] = "Custom"
            st.session_state["dp_open"] = False
            st.rerun()

st.sidebar.markdown("---")

# ── PRESET SHORTCUTS ──────────────────────────────────────────────────────────
_preset_opts = [
    "Last 30 days","Last 7 days","Last 28 days","Last 90 days",
    "This month","Last month","This year","Yesterday","Today"
]
_preset_idx = _preset_opts.index(st.session_state["dp_preset"])     if st.session_state["dp_preset"] in _preset_opts else 0
_chosen = st.sidebar.selectbox("Quick select", _preset_opts, index=_preset_idx, key="dp_quick")
if _chosen != st.session_state["dp_preset"]:
    st.session_state["dp_preset"] = _chosen
    if   _chosen == "Last 7 days":   _ps, _pe = today-timedelta(days=7),  today-timedelta(days=1)
    elif _chosen == "Last 28 days":  _ps, _pe = today-timedelta(days=28), today-timedelta(days=1)
    elif _chosen == "Last 30 days":  _ps, _pe = today-timedelta(days=29), today-timedelta(days=1)
    elif _chosen == "Last 90 days":  _ps, _pe = today-timedelta(days=90), today-timedelta(days=1)
    elif _chosen == "This month":    _ps, _pe = today.replace(day=1),     today-timedelta(days=1)
    elif _chosen == "Last month":
        _ft = today.replace(day=1)
        _pe = _ft - timedelta(days=1)
        _ps = _pe.replace(day=1)
    elif _chosen == "This year":     _ps, _pe = today.replace(month=1, day=1), today-timedelta(days=1)
    elif _chosen == "Yesterday":     _ps, _pe = today-timedelta(days=1), today-timedelta(days=1)
    else:                            _ps, _pe = today, today
    st.session_state["dp_start"] = _ps
    st.session_state["dp_end"]   = _pe
    st.rerun()

# ── Resolve start_date / end_date for the rest of the app ─────────────────────
start_date = st.session_state["dp_start"]
end_date   = st.session_state["dp_end"]

st.sidebar.markdown("---")

# ── COMPARE ───────────────────────────────────────────────────────────────────
compare = st.sidebar.toggle("Compare to previous period", value=False)
if compare:
    period_days = (end_date - start_date).days + 1
    prev_end    = start_date - timedelta(days=1)
    prev_start  = prev_end - timedelta(days=period_days - 1)
    st.sidebar.caption(f"vs {prev_start.strftime('%d %b')} – {prev_end.strftime('%d %b %Y')}")
    with st.sidebar.expander("Custom comparison range"):
        prev_start = st.date_input("Compare from", prev_start, key="cmp_start")
        prev_end   = st.date_input("Compare to",   prev_end,   key="cmp_end")

st.sidebar.markdown("---")
load = st.sidebar.button("Load / Refresh Data", type="primary", use_container_width=True)

# ── MAIN ──────────────────────────────────────────────────────────────────────
st.title("Customer Success Website Analytics Dashboard")
st.caption("Live data — Google Analytics 4 & Google Search Console")

if not load:
    st.info("Select a date range from the sidebar and click **Load / Refresh Data** to begin.")

# Reset permission error flag on each load
if load:
    _GA4_PERMISSION_ERROR = False
    _GA4_PERMISSION_MSG   = ""
st.markdown("---")

# ════════════════════════════════════════════════════════════════════
# WEBSITE + SEARCH CONSOLE ANALYTICS — DATA ON DEMAND
# ════════════════════════════════════════════════════════════════════
st.markdown("## Website + Search Console Analytics")
st.caption(
    "Ask any question about this property's data in plain English. "
    "The AI will fetch the exact numbers from Google Analytics 4 or Google Search Console "
    "and return a table, chart, and Excel download."
)

# ── Groq API key — auto-loaded from Streamlit Secrets, fallback to manual ────
def _get_groq_key():
    # 1. Streamlit Secrets (cloud deployment — preferred)
    try:
        if hasattr(st, "secrets") and "groq_api_key" in st.secrets:
            return st.secrets["groq_api_key"]
    except Exception:
        pass
    # 2. Environment variable (optional local setup)
    import os
    if os.environ.get("GROQ_API_KEY"):
        return os.environ["GROQ_API_KEY"]
    # 3. Manual entry fallback (shown only if key not found above)
    return None

_auto_key = _get_groq_key()
if _auto_key:
    claude_key = _auto_key
else:
    claude_key = st.text_input(
        "Groq API Key",
        type="password",
        placeholder="gsk_...",
        help="Key not found in Streamlit Secrets. Enter manually or ask your admin to add groq_api_key to Streamlit Secrets.",
    )

# ── GA4 dimension/metric schema for Claude ────────────────────────────────
GA4_SCHEMA = """
Available GA4 dimensions: sessionDefaultChannelGroup, deviceCategory, city, country,
landingPage, pagePath, year, month, date, sessionSourceMedium, browser, operatingSystem.

Available GA4 metrics: sessions, activeUsers, newUsers, engagementRate, bounceRate,
averageSessionDuration, screenPageViews, conversions, totalRevenue, eventCount.

Available GSC dimensions: query, page, country, device, date.
Available GSC metrics: clicks, impressions, ctr, position.
"""

# ── Query interpreter via Claude API ─────────────────────────────────────
def interpret_query(user_query, api_key, property_name, start_str, end_str):
    """
    Send the user query to Claude. Claude returns a JSON instruction:
    {
      "source": "ga4" | "gsc",
      "title": "Human-readable title for the result",
      "chart_type": "bar" | "line" | "table_only",
      "x_axis": "column name for x axis",
      "y_axis": "column name for y axis",
      "ga4": {
        "dimensions": [...],
        "metrics": [...],
        "order_by_metric": "metric_name",
        "limit": 25,
        "filter_channel": null | "Organic Search" | etc
      },
      "gsc": {
        "dimensions": ["query"|"page"|"country"|"device"],
        "row_limit": 25,
        "order_by": "clicks"|"impressions"|"position"
      }
    }
    """
    client = Groq(api_key=api_key)
    today_str = str(date.today())
    prompt = f"""You are a data fetching assistant for a hotel website analytics dashboard.
The active property is: {property_name}
Today's date: {today_str}
Default date range: {start_str} to {end_str}

{GA4_SCHEMA}

Interpret the user request and return ONLY a valid JSON object — no markdown, no explanation.

If the query asks for a COMPARISON between two periods (e.g. "Q1 2026 vs Q1 2025", "this year vs last year",
"January vs December"), include BOTH date ranges using "date_ranges" as a list of objects with "start" and "end".
Otherwise use a single "date_range" object.

Example for comparison query:
{{
  "source": "ga4",
  "title": "Organic Traffic Q1 2026 vs Q1 2025",
  "chart_type": "bar",
  "x_axis": "month",
  "y_axis": "sessions",
  "is_comparison": true,
  "date_ranges": [
    {{"label": "Q1 2026", "start": "2026-01-01", "end": "2026-03-31"}},
    {{"label": "Q1 2025", "start": "2025-01-01", "end": "2025-03-31"}}
  ],
  "ga4": {{"dimensions": ["year","month"], "metrics": ["sessions"], "order_by_metric": "sessions", "order_desc": false, "limit": 25, "filter_channel": "Organic Search"}},
  "gsc": {{"dimensions": ["query"], "row_limit": 25, "order_by": "clicks"}}
}}

Example for single period query:
{{
  "source": "ga4",
  "title": "short title",
  "chart_type": "bar",
  "x_axis": "column_name",
  "y_axis": "column_name",
  "is_comparison": false,
  "date_range": {{"start": "{start_str}", "end": "{end_str}"}},
  "ga4": {{"dimensions": ["sessionDefaultChannelGroup"], "metrics": ["sessions"], "order_by_metric": "sessions", "order_desc": true, "limit": 25, "filter_channel": null}},
  "gsc": {{"dimensions": ["query"], "row_limit": 25, "order_by": "clicks"}}
}}

Rules:
- source: "ga4" or "gsc"
- For trends/monthly: dimensions=["year","month"], chart_type="line"
- For breakdowns: chart_type="bar"
- For keywords: source="gsc"
- filter_channel maps to GA4 channel group e.g. "Organic Search", "Direct", "Paid Search"
- For comparisons: always use is_comparison=true and include both periods in date_ranges
- Always infer exact dates from the query. Q1 = Jan-Mar, Q2 = Apr-Jun, Q3 = Jul-Sep, Q4 = Oct-Dec
- Return ONLY the JSON. No markdown fences.

User request: {user_query}"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=512,
    )
    raw = response.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)

def generate_text_insight(user_query, df, api_key, property_name):
    """
    Given the query and the resulting dataframe, ask Groq to write
    a plain-English analytical response with key insights and observations.
    """
    client = Groq(api_key=api_key)
    # Convert df to a compact string for the prompt
    data_str = df.to_string(index=False, max_rows=50)
    prompt = f"""You are a hotel website analytics expert working for a Customer Success team at Simplotel.
The property is: {property_name}
The team asked: "{user_query}"
Here is the data that was retrieved:

{data_str}

Write a clear, concise analytical response in plain English. Structure it as:
1. A 1-2 sentence direct answer to the question.
2. 3-5 bullet points with the most important observations from the data.
3. 1-2 sentences on what this means for the hotel and any recommended action.

Keep it professional but conversational. Do not use technical jargon. Focus on what matters to a hotel marketer."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=600,
    )
    return response.choices[0].message.content.strip()

# ── Execute GA4 query from instruction ────────────────────────────────────
def execute_ga4_query(instruction, start_str, end_str):
    creds   = get_credentials()
    client  = BetaAnalyticsDataClient(credentials=creds)
    g       = instruction.get("ga4", {})
    dims    = [Dimension(name=d) for d in g.get("dimensions", ["sessionDefaultChannelGroup"])]
    metrics = [Metric(name=m) for m in g.get("metrics", ["sessions"])]

    req_kwargs = dict(
        property=f"properties/{PROPERTY_ID}",
        date_ranges=[DateRange(start_date=start_str, end_date=end_str)],
        dimensions=dims,
        metrics=metrics,
        limit=g.get("limit", 25),
    )

    # Order by
    order_metric = g.get("order_by_metric")
    order_desc   = g.get("order_desc", True)
    if order_metric:
        req_kwargs["order_bys"] = [
            OrderBy(metric=OrderBy.MetricOrderBy(metric_name=order_metric), desc=order_desc)
        ]

    # Channel filter
    fc = g.get("filter_channel")
    if fc:
        req_kwargs["dimension_filter"] = FilterExpression(
            filter=Filter(
                field_name="sessionDefaultChannelGroup",
                string_filter=Filter.StringFilter(value=fc)
            )
        )

    resp = client.run_report(RunReportRequest(**req_kwargs))
    rows = []
    dim_names    = [d.name for d in dims]
    metric_names = [m.name for m in metrics]
    for row in resp.rows:
        r = {}
        for i, d in enumerate(dim_names):
            r[d] = row.dimension_values[i].value
        for i, m in enumerate(metric_names):
            try:
                r[m] = float(row.metric_values[i].value)
            except ValueError:
                r[m] = row.metric_values[i].value
        rows.append(r)
    df = pd.DataFrame(rows)
    # Round float columns sensibly
    for col in df.select_dtypes(include="float").columns:
        if "rate" in col.lower() or "ctr" in col.lower():
            df[col] = (df[col] * 100).round(1) if df[col].max() <= 1 else df[col].round(1)
        else:
            df[col] = df[col].round(0).astype(int)
    return df

# ── Execute GSC query from instruction ────────────────────────────────────
def execute_gsc_query(instruction, start_str, end_str):
    if not gsc_available:
        return pd.DataFrame()
    creds   = get_credentials()
    service = build("searchconsole", "v1", credentials=creds)
    g       = instruction.get("gsc", {})
    body = {
        "startDate":  start_str,
        "endDate":    end_str,
        "dimensions": g.get("dimensions", ["query"]),
        "rowLimit":   g.get("row_limit", 25),
        "orderBy":    [{"fieldName": g.get("order_by", "clicks"), "sortOrder": "DESCENDING"}],
    }
    resp = service.searchanalytics().query(siteUrl=SITE_URL, body=body).execute()
    rows = []
    for row in resp.get("rows", []):
        r = {d: row["keys"][i] for i, d in enumerate(g.get("dimensions", ["query"]))}
        r["clicks"]      = int(row.get("clicks", 0))
        r["impressions"] = int(row.get("impressions", 0))
        r["ctr"]         = round(row.get("ctr", 0) * 100, 1)
        r["position"]    = round(row.get("position", 0), 1)
        rows.append(r)
    return pd.DataFrame(rows)

# ── Render chart from instruction + dataframe ─────────────────────────────
def render_query_chart(df, instruction):
    chart_type = instruction.get("chart_type", "bar")
    x_col      = instruction.get("x_axis", df.columns[0])
    y_col      = instruction.get("y_axis", df.columns[1] if len(df.columns) > 1 else df.columns[0])
    title      = instruction.get("title", "Query Result")

    if x_col not in df.columns:
        x_col = df.columns[0]
    if y_col not in df.columns:
        y_col = df.select_dtypes(include="number").columns[0] if len(df.select_dtypes(include="number").columns) > 0 else df.columns[-1]

    if chart_type == "table_only" or len(df) == 0:
        return None

    fig = go.Figure()
    if chart_type == "line":
        fig.add_trace(go.Scatter(
            x=df[x_col].astype(str), y=df[y_col],
            mode="lines+markers+text",
            text=df[y_col].apply(lambda v: f"{v:,}" if isinstance(v, (int, float)) else str(v)),
            textposition="top center", textfont=dict(size=10),
            line=dict(color="#4C8BF5", width=2.5),
            marker=dict(size=7),
            fill="tozeroy", fillcolor="rgba(76,139,245,0.08)",
        ))
    else:
        fig.add_trace(go.Bar(
            x=df[x_col].astype(str), y=df[y_col],
            marker_color="#4C8BF5",
            text=df[y_col].apply(lambda v: f"{v:,}" if isinstance(v, (int, float)) else str(v)),
            textposition="outside", textfont=dict(size=11),
            cliponaxis=False,
        ))

    max_y = df[y_col].max() if pd.api.types.is_numeric_dtype(df[y_col]) else 1
    fig.update_layout(
        title=dict(text=title, font=dict(size=15, family="Arial")),
        plot_bgcolor="white", paper_bgcolor="white",
        font=dict(family="Arial", size=13),
        yaxis=dict(gridcolor="#eeeeee", tickformat=",", rangemode="tozero",
                   range=[0, max_y * 1.25] if pd.api.types.is_numeric_dtype(df[y_col]) else None),
        xaxis=dict(tickfont=dict(size=11), tickangle=-30 if len(df) > 6 else 0),
        margin=dict(t=70, b=80, l=60, r=40),
        height=420,
    )
    return fig

# ── Excel builder ─────────────────────────────────────────────────────────
def build_excel(query_results):
    """
    query_results: list of {"title": str, "df": DataFrame}
    Returns bytes of an Excel workbook with one sheet per result.
    """
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for i, result in enumerate(query_results):
            sheet_name = result["title"][:28].strip() + f" ({i+1})" if len(result["title"]) > 28 else result["title"]
            sheet_name = sheet_name[:31]  # Excel sheet name limit
            result["df"].to_excel(writer, sheet_name=sheet_name, index=False)
    buf.seek(0)
    return buf.getvalue()

# ── Session state for accumulated query results ───────────────────────────
if "query_results" not in st.session_state:
    st.session_state["query_results"] = []

# ── Query input ───────────────────────────────────────────────────────────
with st.form("query_form", clear_on_submit=True):
    user_query = st.text_input(
        "What data do you need?",
        placeholder=(
            "e.g. Top 10 landing pages by sessions last 30 days  ·  "
            "Organic keyword clicks this month  ·  "
            "Device breakdown for last 90 days  ·  "
            "Monthly organic sessions trend this year"
        ),
    )
    run_query = st.form_submit_button("🔍 Run Query", use_container_width=True, type="primary")

if run_query:
    if not user_query.strip():
        st.warning("Please enter a query.")
    elif not claude_key.strip():
        st.warning("Please enter your Groq API key above.")
    else:
        # Date range inferred by AI from query text; fallback = last 90 days
        q_start = str(date.today() - timedelta(days=90))
        q_end   = str(date.today() - timedelta(days=1))
        with st.spinner("Thinking..."):
            try:
                instruction = interpret_query(
                    user_query, claude_key,
                    PROPERTIES[selected_label]["name"],
                    q_start, q_end
                )
                source      = instruction.get("source", "ga4")
                is_comp     = instruction.get("is_comparison", False)
                date_ranges = instruction.get("date_ranges", [])

                if is_comp and date_ranges:
                    # Fetch each period separately and merge with a period label column
                    frames = []
                    for dr in date_ranges:
                        if source == "gsc":
                            df_p = execute_gsc_query(instruction, dr["start"], dr["end"])
                        else:
                            df_p = execute_ga4_query(instruction, dr["start"], dr["end"])
                        if not df_p.empty:
                            df_p.insert(0, "Period", dr.get("label", f"{dr['start']} to {dr['end']}"))
                            frames.append(df_p)
                    df_result = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
                else:
                    # Single period — use date_range from instruction or fallback
                    dr = instruction.get("date_range", {"start": q_start, "end": q_end})
                    if source == "gsc":
                        if not gsc_available:
                            st.error("Google Search Console is not configured for this property.")
                            df_result = pd.DataFrame()
                        else:
                            df_result = execute_gsc_query(instruction, dr["start"], dr["end"])
                    else:
                        df_result = execute_ga4_query(instruction, dr["start"], dr["end"])

                if df_result.empty:
                    st.warning("No data returned for this query and date range.")
                else:
                    title = instruction.get("title", user_query[:60])
                    # Generate text insight — pass full data including both periods
                    with st.spinner("Generating insight..."):
                        try:
                            text_insight = generate_text_insight(
                                user_query, df_result, claude_key,
                                PROPERTIES[selected_label]["name"]
                            )
                        except Exception:
                            text_insight = ""
                    st.session_state["query_results"].append({
                        "title":       title,
                        "query":       user_query,
                        "df":          df_result,
                        "instruction": instruction,
                        "insight":     text_insight,
                    })
            except json.JSONDecodeError:
                st.error("The AI returned an unexpected response. Try rephrasing your query.")
            except Exception as e:
                st.error(f"Error: {e}")

# ── Display accumulated results ───────────────────────────────────────────
if st.session_state["query_results"]:
    col_dl, col_clr = st.columns([3, 1])
    with col_dl:
        excel_bytes = build_excel(st.session_state["query_results"])
        st.download_button(
            label=f"📥 Download all {len(st.session_state['query_results'])} result(s) as Excel",
            data=excel_bytes,
            file_name=f"analytics_queries_{date.today()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    with col_clr:
        if st.button("🗑 Clear all results", use_container_width=True):
            st.session_state["query_results"] = []
            st.rerun()

    # Display in reverse order (newest first)
    results_to_delete = []
    for i, result in enumerate(reversed(st.session_state["query_results"])):
        real_idx = len(st.session_state["query_results"]) - 1 - i
        with st.expander(f"**{result['title']}**  ·  {result['query']}", expanded=(i == 0)):

            # ── AI Text Insight ───────────────────────────────────────────
            if result.get("insight"):
                st.markdown("#### 💡 AI Insight")
                st.info(result["insight"])

            # ── Chart ─────────────────────────────────────────────────────
            fig = render_query_chart(result["df"], result["instruction"])
            if fig:
                st.plotly_chart(fig, use_container_width=True, key=f"qchart_{i}")

            # ── Data Table ────────────────────────────────────────────────
            st.dataframe(result["df"], use_container_width=True, hide_index=True)

            # ── Action Row: Download + Delete ─────────────────────────────
            col_exc, col_del = st.columns([3, 1])
            with col_exc:
                single_excel = build_excel([result])
                st.download_button(
                    label="📥 Download as Excel",
                    data=single_excel,
                    file_name=f"{result['title'][:40]}_{date.today()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"dl_{i}",
                    use_container_width=True,
                )
            with col_del:
                if st.button("🗑 Delete", key=f"del_{i}", use_container_width=True):
                    results_to_delete.append(real_idx)

    # Process deletions after the loop
    if results_to_delete:
        for idx in sorted(results_to_delete, reverse=True):
            del st.session_state["query_results"][idx]
        st.rerun()

st.markdown("---")

# ════════════════════════════════════════════════════════════════════
# DECK METRICS
# ════════════════════════════════════════════════════════════════════
st.markdown(f"## Deck Metrics — {PROPERTIES[selected_label]['name']}")
if _GA4_PERMISSION_ERROR:
    st.warning(
        f"⚠️ The service account does not have access to this property (GA4 ID: {_GA4_PERMISSION_MSG}). "
        f"Charts will be empty. To fix: log into Google Analytics with the account that owns this property, "
        f"go to Admin → Account Access Management, and add "
        f"one of the service accounts (simplotel-dashboard / dashboard-2 / dashboard-3) @cs-analytics-link.iam.gserviceaccount.com as Viewer.",
        icon="🔒"
    )
st.caption(
    "Fixed date windows — independent of the date selector above. "
    "Year-on-Year charts: 2022 to present. "
    "Segmentation: last 24 months. "
    "Locations: last 6 months (Organic Search only). "
    "Google Search Console brand comparison: current year vs previous year, January to today."
)

# ── YOY ALL CHANNELS ──────────────────────────────────────────────────────
st.markdown("### Year-on-Year Traffic — All Channels")
_xg_all = st.selectbox("X-axis grouping", ["Month","Week","Day"], key="xg_all")
with st.spinner("Loading year-on-year data..."):
    if _xg_all == "Month":
        df_yoy = get_ga4_monthly_yoy()
    else:
        _ga4c = BetaAnalyticsDataClient(credentials=get_credentials())
        if _xg_all == "Week":
            _rq = RunReportRequest(
                property=f"properties/{PROPERTY_ID}",
                date_ranges=[DateRange(start_date="2022-01-01", end_date="today")],
                dimensions=[Dimension(name="year"), Dimension(name="week")],
                metrics=[Metric(name="sessions")]
            )
            _rsp = _ga4c.run_report(_rq)
            _rows = [{"year": int(r.dimension_values[0].value),
                      "label": f"Wk {int(r.dimension_values[1].value):02d} · {r.dimension_values[0].value}",
                      "sort": int(r.dimension_values[0].value)*100 + int(r.dimension_values[1].value),
                      "sessions": int(r.metric_values[0].value)} for r in _rsp.rows]
        else:
            import datetime as _dtt
            _rq = RunReportRequest(
                property=f"properties/{PROPERTY_ID}",
                date_ranges=[DateRange(start_date="2024-01-01", end_date="today")],
                dimensions=[Dimension(name="date")],
                metrics=[Metric(name="sessions")]
            )
            _rsp = _ga4c.run_report(_rq)
            _rows = [{"year": int(r.dimension_values[0].value[:4]),
                      "label": _dtt.datetime.strptime(r.dimension_values[0].value, "%Y%m%d").strftime("%d %b %Y"),
                      "sort": int(r.dimension_values[0].value),
                      "sessions": int(r.metric_values[0].value)} for r in _rsp.rows]
        df_yoy = pd.DataFrame(_rows).sort_values("sort")

if not df_yoy.empty:
    years   = sorted(df_yoy["year"].unique())
    fig_yoy = go.Figure()
    if _xg_all == "Month":
        for i, year in enumerate(years):
            df_y   = df_yoy[df_yoy["year"] == year].set_index("month")
            y_vals = [int(df_y.loc[m, "sessions"]) if m in df_y.index else None for m in range(1, 13)]
            t_vals = [f"{v:,}" if v else "" for v in y_vals]
            fig_yoy.add_trace(go.Bar(
                name=str(year), x=MONTH_LABELS, y=y_vals,
                text=t_vals, textposition="outside", textfont=dict(size=10),
                marker_color=YEAR_COLORS[i % len(YEAR_COLORS)], cliponaxis=False,
            ))
    else:
        for i, year in enumerate(years):
            df_y = df_yoy[df_yoy["year"] == year]
            fig_yoy.add_trace(go.Bar(
                name=str(year), x=df_y["label"], y=df_y["sessions"],
                text=df_y["sessions"].apply(lambda v: f"{v:,}"),
                textposition="outside", textfont=dict(size=9),
                marker_color=YEAR_COLORS[i % len(YEAR_COLORS)], cliponaxis=False,
            ))
    max_yoy = df_yoy["sessions"].max()
    layout  = yoy_layout("Overall Sessions")
    layout["yaxis"]["range"] = [0, max_yoy * 1.25]
    if _xg_all != "Month":
        layout["xaxis"] = dict(tickfont=dict(size=9), tickangle=-45)
    fig_yoy.update_layout(**layout)
    st.plotly_chart(fig_yoy, use_container_width=True)

# ── YOY ORGANIC ───────────────────────────────────────────────────────────
st.markdown("### Year-on-Year Traffic — Organic Search Only")
_xg_org = st.selectbox("X-axis grouping", ["Month","Week","Day"], key="xg_org")
with st.spinner("Loading organic year-on-year data..."):
    if _xg_org == "Month":
        df_yoy_org = get_ga4_monthly_yoy_organic()
    else:
        _ga4o = BetaAnalyticsDataClient(credentials=get_credentials())
        _flt  = FilterExpression(filter=Filter(
            field_name="sessionDefaultChannelGroup",
            string_filter=Filter.StringFilter(value="Organic Search")
        ))
        if _xg_org == "Week":
            _rqo = RunReportRequest(
                property=f"properties/{PROPERTY_ID}",
                date_ranges=[DateRange(start_date="2022-01-01", end_date="today")],
                dimensions=[Dimension(name="year"), Dimension(name="week")],
                metrics=[Metric(name="sessions")],
                dimension_filter=_flt
            )
            _rspo = _ga4o.run_report(_rqo)
            _rowso = [{"year": int(r.dimension_values[0].value),
                       "label": f"Wk {int(r.dimension_values[1].value):02d} · {r.dimension_values[0].value}",
                       "sort": int(r.dimension_values[0].value)*100 + int(r.dimension_values[1].value),
                       "sessions": int(r.metric_values[0].value)} for r in _rspo.rows]
        else:
            import datetime as _dtt2
            _rqo = RunReportRequest(
                property=f"properties/{PROPERTY_ID}",
                date_ranges=[DateRange(start_date="2024-01-01", end_date="today")],
                dimensions=[Dimension(name="date")],
                metrics=[Metric(name="sessions")],
                dimension_filter=_flt
            )
            _rspo = _ga4o.run_report(_rqo)
            _rowso = [{"year": int(r.dimension_values[0].value[:4]),
                       "label": _dtt2.datetime.strptime(r.dimension_values[0].value, "%Y%m%d").strftime("%d %b %Y"),
                       "sort": int(r.dimension_values[0].value),
                       "sessions": int(r.metric_values[0].value)} for r in _rspo.rows]
        df_yoy_org = pd.DataFrame(_rowso).sort_values("sort")

if not df_yoy_org.empty:
    years_org   = sorted(df_yoy_org["year"].unique())
    fig_yoy_org = go.Figure()
    if _xg_org == "Month":
        for i, year in enumerate(years_org):
            df_y   = df_yoy_org[df_yoy_org["year"] == year].set_index("month")
            y_vals = [int(df_y.loc[m, "sessions"]) if m in df_y.index else None for m in range(1, 13)]
            t_vals = [f"{v:,}" if v else "" for v in y_vals]
            fig_yoy_org.add_trace(go.Bar(
                name=str(year), x=MONTH_LABELS, y=y_vals,
                text=t_vals, textposition="outside", textfont=dict(size=10),
                marker_color=YEAR_COLORS[i % len(YEAR_COLORS)], cliponaxis=False,
            ))
    else:
        for i, year in enumerate(years_org):
            df_y = df_yoy_org[df_yoy_org["year"] == year]
            fig_yoy_org.add_trace(go.Bar(
                name=str(year), x=df_y["label"], y=df_y["sessions"],
                text=df_y["sessions"].apply(lambda v: f"{v:,}"),
                textposition="outside", textfont=dict(size=9),
                marker_color=YEAR_COLORS[i % len(YEAR_COLORS)], cliponaxis=False,
            ))
    max_org = df_yoy_org["sessions"].max()
    layout  = yoy_layout("Organic Sessions")
    layout["yaxis"]["range"] = [0, max_org * 1.25]
    if _xg_org != "Month":
        layout["xaxis"] = dict(tickfont=dict(size=9), tickangle=-45)
    fig_yoy_org.update_layout(**layout)
    st.plotly_chart(fig_yoy_org, use_container_width=True)

st.markdown("---")

# ── TRAFFIC SEGMENTATION — MONTHLY STACKED ───────────────────────────────
st.markdown("### Traffic Segmentation — Month-wise (Excluding Organic Search)")
st.caption("Last 24 months · Stacked by channel · Organic Search has its own chart above.")
with st.spinner("Loading segmentation data..."):
    df_seg = get_ga4_segmentation_monthly()

if not df_seg.empty:
    month_order  = (df_seg[["sort_key","month_label"]]
                    .drop_duplicates()
                    .sort_values("sort_key")["month_label"]
                    .tolist())
    channels_seg = df_seg["channel"].unique().tolist()
    fig_seg      = go.Figure()
    for ch in channels_seg:
        df_ch  = df_seg[df_seg["channel"] == ch].set_index("month_label")
        y_vals = [int(df_ch.loc[m, "sessions"]) if m in df_ch.index else 0 for m in month_order]
        fig_seg.add_trace(go.Bar(
            name=ch,
            x=month_order,
            y=y_vals,
            marker_color=SEGMENT_COLORS.get(ch, "#BBBBBB"),
            text=[f"{v:,}" if v > 0 else "" for v in y_vals],
            textposition="inside",
            textfont=dict(size=9, color="white"),
        ))
    max_seg = df_seg.groupby(["sort_key","month_label"])["sessions"].sum().max()
    fig_seg.update_layout(
        **BASE,
        barmode="stack",
        yaxis=dict(
            title="Sessions", gridcolor="#eeeeee", tickformat=",",
            range=[0, max_seg * 1.15], title_font=dict(size=13)
        ),
        xaxis=dict(title="", tickangle=-45, tickfont=dict(size=11)),
        legend=dict(orientation="h", yanchor="bottom", y=1.03, xanchor="center", x=0.5, font=dict(size=12)),
        margin=dict(t=80, b=100, l=70, r=40),
        height=520,
    )
    st.plotly_chart(fig_seg, use_container_width=True)

st.markdown("---")

# ── ENGAGEMENT RATE — MONTHLY LINE ────────────────────────────────────────
st.markdown("### Engagement Rate — Month-wise (Organic Search Only)")
st.caption("Last 6 months · Fixed window · Organic Search only.")
_eng_end   = date.today() - timedelta(days=1)
_eng_start = date.today() - timedelta(days=180)
with st.spinner("Loading engagement rate data..."):
    df_eng = get_ga4_monthly_engagement(_eng_start, _eng_end)

if not df_eng.empty:
    fig_eng = go.Figure()
    fig_eng.add_trace(go.Scatter(
        x=df_eng["label"], y=df_eng["engagement_rate"],
        mode="lines+markers+text",
        text=[f"{v}%" for v in df_eng["engagement_rate"]],
        textposition="top center", textfont=dict(size=12),
        line=dict(color="#4C8BF5", width=2.5),
        marker=dict(size=8),
        fill="tozeroy", fillcolor="rgba(76,139,245,0.08)",
    ))
    fig_eng.update_layout(
        **BASE,
        yaxis=dict(
            title="Engagement Rate (%)", gridcolor="#eeeeee",
            range=[0, 110], title_font=dict(size=13)
        ),
        xaxis=dict(
            title="", tickfont=dict(size=12),
            range=[-0.5, len(df_eng) - 0.5],
        ),
        margin=dict(t=50, b=70, l=70, r=80),
        height=400,
    )
    fig_eng.update_traces(cliponaxis=False)
    st.plotly_chart(fig_eng, use_container_width=True)

st.markdown("---")

# ── DEVICE SPLIT ─────────────────────────────────────────────────────────
st.markdown("### Traffic Split — Device Wise")
with st.spinner("Loading device data..."):
    df_device = get_ga4_device(start_date, end_date)

if not df_device.empty:
    dev_colors = ["#4C8BF5", "#34A853", "#FBBC04", "#EA4335"]
    col_pie, col_table = st.columns([1, 1])

    with col_pie:
        fig_pie = go.Figure(go.Pie(
            labels=df_device["Device"],
            values=df_device["Sessions"],
            hole=0.45,
            marker=dict(colors=dev_colors[:len(df_device)]),
            textinfo="label+percent+value",
            textfont=dict(size=13),
            texttemplate="%{label}<br>%{value:,} (%{percent})",
            hovertemplate="<b>%{label}</b><br>Sessions: %{value:,}<br>Share: %{percent}<extra></extra>",
            insidetextorientation="radial",
        ))
        fig_pie.update_layout(
            **BASE,
            showlegend=False,
            margin=dict(t=30, b=30, l=30, r=30),
            height=380,
            annotations=[dict(text="Sessions", x=0.5, y=0.5, font=dict(size=15, family="Arial"), showarrow=False)]
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_table:
        st.markdown("&nbsp;")
        st.dataframe(df_device, use_container_width=True, hide_index=True)

st.markdown("---")

# ── TOP 10 CITIES & COUNTRIES ─────────────────────────────────────────────
st.markdown("### Organic Traffic — Top Locations (Past 6 Months)")
st.caption("Organic Search channel only · Last 180 days · Fixed window.")

col_cities, col_countries = st.columns(2)

with col_cities:
    st.markdown("#### Top 10 Cities")
    with st.spinner("Loading city data..."):
        df_cities = get_ga4_top_cities()
    if not df_cities.empty:
        max_city = df_cities["Sessions"].max()
        fig_cities = go.Figure(go.Bar(
            x=df_cities["Sessions"],
            y=df_cities["City"],
            orientation="h",
            marker_color="#4C8BF5",
            text=df_cities["Sessions"].apply(lambda x: f"{x:,}"),
            textposition="outside",
            textfont=dict(size=12),
            cliponaxis=False,
        ))
        fig_cities.update_layout(**horiz_bar_layout("Sessions", max_city))
        st.plotly_chart(fig_cities, use_container_width=True)

with col_countries:
    st.markdown("#### Top 10 Countries")
    with st.spinner("Loading country data..."):
        df_countries = get_ga4_top_countries()
    if not df_countries.empty:
        max_country = df_countries["Sessions"].max()
        fig_countries = go.Figure(go.Bar(
            x=df_countries["Sessions"],
            y=df_countries["Country"],
            orientation="h",
            marker_color="#34A853",
            text=df_countries["Sessions"].apply(lambda x: f"{x:,}"),
            textposition="outside",
            textfont=dict(size=12),
            cliponaxis=False,
        ))
        fig_countries.update_layout(**horiz_bar_layout("Sessions", max_country))
        st.plotly_chart(fig_countries, use_container_width=True)

st.markdown("---")

# ── GSC BRAND vs NON-BRAND ────────────────────────────────────────────────
st.markdown("### Google Search Console — Brand vs Non-Brand Queries")
if not gsc_available:
    st.info("Google Search Console is not configured for this property. Add the GSC URL to PROPERTIES in app.py.")
elif not BRAND_KEYWORDS:
    st.info("No brand keywords configured for this property. Add them to the PROPERTIES dict in app.py.")
else:
    st.caption(
        f"Current year ({today.year}) vs previous year ({today.year - 1}) · "
        "January 1 to today's date, both years."
    )

    ytd_end   = today
    ytd_start = date(today.year - 1, 1, 1)
    this_year = str(today.year)
    last_year = str(today.year - 1)

    with st.spinner("Loading brand and non-brand data (this may take a moment)..."):
        df_brand, df_nonbrand = get_gsc_brand_nonbrand(ytd_start, ytd_end)

    def filter_year(df, yr):
        if df.empty:
            return pd.DataFrame()
        return df[df["month"].astype(str).str.startswith(yr)].copy()

    col_brand, col_nb = st.columns(2)
    with col_brand:
        fig_b = gsc_clean_chart(
            filter_year(df_brand, this_year),
            filter_year(df_brand, last_year),
            this_year, last_year,
            "Brand Queries",
            "#4C8BF5", "#aac4f7"
        )
        st.plotly_chart(fig_b, use_container_width=True)

    with col_nb:
        fig_nb = gsc_clean_chart(
            filter_year(df_nonbrand, this_year),
            filter_year(df_nonbrand, last_year),
            this_year, last_year,
            "Non-Brand Queries",
            "#34A853", "#a8d9b5"
        )
        st.plotly_chart(fig_nb, use_container_width=True)

st.markdown("---")
# ── GA4 CHANNEL (Google Analytics: Custom Chart) ────────────────────────────
st.markdown("### Google Analytics: Custom Chart")
with st.spinner("Loading channel data..."):
    df_ga4 = get_ga4_data(start_date, end_date)

if df_ga4.empty:
    st.info("No data available for this property. The service account may not have access to this Google Analytics 4 property yet. Ask your admin to add simplotel-dashboard@cs-analytics-link.iam.gserviceaccount.com as Viewer in Google Analytics.", icon="🔒")
else:
    total_sessions = df_ga4["sessions"].sum()
    top_channel    = df_ga4.iloc[0]["channel"] if not df_ga4.empty else "—"
    org_eng        = df_ga4[df_ga4["channel"] == "Organic Search"]["engagement"].values
    org_eng_val    = f"{org_eng[0]}%" if len(org_eng) else "—"

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Sessions",          f"{total_sessions:,}")
    c2.metric("Top Channel",              top_channel)
    c3.metric("Organic Engagement Rate",  org_eng_val)

    if compare:
        df_ga4_prev = get_ga4_data(prev_start, prev_end)
        fig_ga4 = go.Figure()
        fig_ga4.add_trace(go.Bar(
            name=f"Current  ({start_date.strftime('%d %b')} – {end_date.strftime('%d %b %Y')})",
            x=df_ga4["channel"], y=df_ga4["sessions"],
            marker_color="#4C8BF5",
            text=df_ga4["sessions"].apply(lambda x: f"{x:,}"),
            textposition="outside", textfont=dict(size=11), cliponaxis=False,
        ))
        fig_ga4.add_trace(go.Bar(
            name=f"Previous ({prev_start.strftime('%d %b')} – {prev_end.strftime('%d %b %Y')})",
            x=df_ga4_prev["channel"], y=df_ga4_prev["sessions"],
            marker_color="#AACDE8",
            text=df_ga4_prev["sessions"].apply(lambda x: f"{x:,}"),
            textposition="outside", textfont=dict(size=11), cliponaxis=False,
        ))
    else:
        fig_ga4 = go.Figure(go.Bar(
            x=df_ga4["channel"], y=df_ga4["sessions"],
            text=df_ga4["sessions"].apply(lambda x: f"{x:,}"),
            textposition="outside", textfont=dict(size=12),
            marker_color="#4C8BF5", cliponaxis=False,
        ))
    max_ga4 = df_ga4["sessions"].max() if not df_ga4.empty else 1
    fig_ga4.update_layout(
        **BASE,
        barmode="group",
        yaxis=dict(gridcolor="#eeeeee", tickformat=",", range=[0, max_ga4 * 1.25]),
        xaxis=dict(tickfont=dict(size=12)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=12)),
        height=420, margin=dict(t=60, b=60, l=70, r=40)
    )
    st.plotly_chart(fig_ga4, use_container_width=True, key="fig_ga4_custom")

    # Auto-generate delta metrics when compare is on
    if compare and not df_ga4_prev.empty:
        st.markdown("**Channel comparison — period over period**")
        _prev_dict = dict(zip(df_ga4_prev["channel"], df_ga4_prev["sessions"]))
        _delta_cols = st.columns(min(len(df_ga4), 5))
        for _ci, (_, _row) in enumerate(df_ga4.iterrows()):
            if _ci >= 5:
                break
            _prev_val = _prev_dict.get(_row["channel"], 0)
            _delta_n  = _row["sessions"] - _prev_val
            _pct      = round(_delta_n / _prev_val * 100, 1) if _prev_val > 0 else 0
            _delta_cols[_ci].metric(
                label=_row["channel"][:16],
                value=f"{_row['sessions']:,}",
                delta=f"{_pct:+.1f}%"
            )

# ── GSC TOP KEYWORDS ──────────────────────────────────────────────────────
st.markdown("### Google Search Console — Top Keywords")
if gsc_available:
    with st.spinner("Loading keyword data..."):
        df_gsc = get_gsc_data(start_date, end_date)
    if not df_gsc.empty:
        g1, g2, g3, g4 = st.columns(4)
        g1.metric("Total Clicks",      f"{df_gsc['Clicks'].sum():,}")
        g2.metric("Total Impressions",  f"{df_gsc['Impressions'].sum():,}")
        g3.metric("Average CTR",        f"{round(df_gsc['CTR (%)'].mean(), 1)}%")
        g4.metric("Average Position",   f"{round(df_gsc['Position'].mean(), 1)}")
        st.dataframe(df_gsc, use_container_width=True, hide_index=True)
else:
    st.info("Google Search Console is not configured for this property. Add the GSC URL to PROPERTIES in app.py to enable this section.")
