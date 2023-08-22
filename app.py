import sys
import pandas as pd
import numpy as np
import streamlit as st

st.set_page_config(page_title='Lapangbola Passing Network Dashboard', layout='wide')
st.header('Assign xG value to shots')
st.markdown('Created by: Prana - R&D Division Lapangbola.com')

sys.path.append("listfungsi.py")
from listfungsi import get_PNdata
from listfungsi import plot_PN

with st.expander("BACA INI DULU."):
    st.write("")
    
col1, col2 = st.columns(2)
with col1:
    tl_data = st.file_uploader("Upload file timeline excel!")
    tl = pd.read_excel(tl_data, skiprows=[0])

with col2:
    rp_data = st.file_uploader("Upload file report excel!")
    rp = pd.read_excel(rp_data, skiprows=[0])
    team1 = rp['Team'][0]
    team2 = rp['Opponent'][0]
    match = team1 +' vs '+team2
            
colx, coly, colz = st.columns(3)
with colx:
    filter = st.selectbox('Select Team', [team1, team2])
with coly:
    min_pass = st.number_input('Select Min. Successful Passes', min_value=0, max_value=3, step=1)
with colz:
    menit = st.slider('Select Minutes', 0, 90, (1, 30))
        
plotdata = get_PNdata(tl, rp, menit[0], menit[1], filter, min_pass)
pass_between = plotdata[0]
        
if 'clicked' not in st.session_state:
    st.session_state.clicked = False
        
def click_button():
    st.session_state.clicked = True
            
st.button('Rekomenasikan menit!', on_click=click_button)
if st.session_state.clicked:
    st.write('Untuk tim ini direkomendasikan memilih menit 1 hingga '+plotdata[1])
        
pn = plot_PN(pass_between, min_pass, filter, menit[0], menit[1], match)
        
with open('/app/lb-passingnetwork/data/pnet.jpg', 'rb') as img:
    fn = 'PN_'+filter+'-'+f_team+'.jpg'
    btn = st.download_button(label="Download Passing Network", data=img, file_name=fn, mime="image/jpg")
st.pyplot(pn)
