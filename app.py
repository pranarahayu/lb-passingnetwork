import sys
import pandas as pd
import numpy as np
import streamlit as st

st.set_page_config(page_title='Lapangbola Passing Network Dashboard', layout='wide')
st.header('Passing Network Generator')
st.markdown('Created by: Prana - R&D Division Lapangbola.com')

sys.path.append("listfungsi.py")
from listfungsi import get_PNdata
from listfungsi import plot_PN

with st.expander("BACA INI DULU."):
    st.write("Upload file timeline yang telah selesai di-QC!")
    
col1, col2 = st.columns(2)
with col1:
    tl_data = st.file_uploader("Upload file timeline excel!")
    try:
        tl = pd.read_excel(tl_data, skiprows=[0])
    except ValueError:
        st.error("Please upload the timeline file")

with col2:
    rp_data = st.file_uploader("Upload file report excel!")
    try:
        rp = pd.read_excel(rp_data, skiprows=[0])
        team1 = rp['Team'][0]
        team2 = rp['Opponent'][0]
        goal1 = rp['Result'].str.split(' -').str[0]
        goal2 = rp['Result'].str.split('- ').str[1]
        mw = rp['Gameweek'][0]
        match = team1.upper() +' '+goal1+' vs '+goal2+' '+team2.upper()
        match = match[0]
        #match = team1+' vs '+team2
    except ValueError:
        st.error("Please upload the excel report file")
            
colx, coly, colz, cola = st.columns(4)
with colx:
    filter = st.selectbox('Select Team', [team1, team2])
with coly:
    min_pass = st.number_input('Select Min. Successful Passes', min_value=1, max_value=5, step=1)
with colz:
    menit = st.slider('Select Minutes', 0, 91, (1, 30))
with cola:
    komp = st.selectbox('Select Competition', ['Liga 1 2023/24', 'Liga 2 2023/24'])
    gw = komp+' | GW '+str(mw)
        
plotdata = get_PNdata(tl, rp, menit[0], menit[1], filter)
pass_between = plotdata[0]
        
if 'clicked' not in st.session_state:
    st.session_state.clicked = False
        
def click_button():
    st.session_state.clicked = True
            
st.button('Subs/Red Cards', on_click=click_button)
if st.session_state.clicked:
    st.write('Menit-menit pergantian dan/atau kartu merah: '+str(plotdata[1]))

pn = plot_PN(pass_between, min_pass, filter, menit[0], menit[1], match, gw)
st.pyplot(pn)

with open('pnet.jpg', 'rb') as img:
    fn = 'PN_'+filter+'.jpg'
    btn = st.download_button(label="Download Passing Network", data=img, file_name=fn, mime="image/jpg")
