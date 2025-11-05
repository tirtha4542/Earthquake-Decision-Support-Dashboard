import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
from datetime import datetime,timedelta
import warnings
import streamlit as st
warnings.filterwarnings('ignore')

st.set_page_config(
    page_title="Earthquake Decision Support Dashboard",
    layout="wide",
    initial_sidebar_state='expanded',

)

#Add a Page Title

st.title("Earthquake Decision Support Dashboard")
st.markdown(
    "**real-time monitoring**"
)

uploded_file=st.file_uploader("Choose earthquake CSV",type=["csv"])

#Read CSV to DF

def load_and_process_data(uploded_file):
    # step 1:Read CSV to DF
    df = pd.read_csv(uploded_file)

    #step 2:Convert the Time column into Date time format

    df["time"]=pd.to_datetime(
        df["time"],format='%Y-%m-%d %H:%M:%S.%f',errors='coerce'
    )
    # step 3:Drop rows where time is missing
    df = df.dropna(subset=['time'])
    # convert time into date,year,month,hour etc
    df["date"] = df['time'].dt.date
    df["Year"] = df['time'].dt.year
    df["month"] = df['time'].dt.month
    df['hour'] = df['time'].dt.hour 
    df["day_of_week"] = df['time'].dt.day_name() 

    df["risk_level"] = pd.cut(
        df["magnitude"],
        bins=[0,4.0,5.5,6.5,np.inf],
        labels=['LOW','Moderate','High','Critical']
    )

    df["tectonic_type"] = np.where(
        df['depth']<70,'Crustal',
        np.where(
            df["depth"]<300,"intermediate",'deep'
        )
    )
    #cluster Detection
    df = df.sort_values('time').reset_index(drop=True)
    df['hours_since_prev'] = df["time"].diff().dt.total_seconds()/3600
    df['hours_since_prev']  =  df['hours_since_prev'].fillna(0)
    df['cluster_flag'] =  df['hours_since_prev'] <24
    return df
if uploded_file is not None:
    st.markdown("uploaded file Successfully")
    with st.spinner("Loading..."):
        df = load_and_process_data(uploded_file)
    st.markdown("---") #create a horijontal Line
    
    st.sidebar.header("Filter")

    time_window = st.sidebar.selectbox(
            "Time Window",
            ["All Time","Last 7 Day","Last 30 day","Last 90 day","Custom"]
    
        )  
    if time_window=="Custom":
            start_date = st.sidebar.date_input("start",df['date'].min())
            end_date = st.sidebar.date_input("End",df['date'].max())  

            filter_df = df[(df["date"]>=start_date)&(df['date']<=end_date)]
    else:
            days = {"All Time":9999,"Last 7 Day":7,"Last 30 day":30,"Last 90 day":90}

            cutoff = df['time'].max() - timedelta(days = days[time_window])
            filter_df = df[df['time']>=cutoff]
    deepth_range = st.sidebar.slider(
            "Depth (KM)",
            float(df['depth'].min()),float(df["depth"].max()),(float(df['depth'].min()),float(df["depth"].max()))
        )

    mag_range = st.sidebar.slider(
         
            "Magnitude",
            float(df['magnitude'].min()),float(df["magnitude"].max()),(float(df['magnitude'].min()),float(df['magnitude'].max()))

        )
    #risk & tectonic

    risk_lavels = st.sidebar.multiselect(
        "Risk Lavel",
        ["Low","Moderate","High","Critical"],
        default=["Moderate","High","Critical"]
    )
    techtonic_type = st.sidebar.multiselect(
        "Techtonic Type",
        ["Crustal","Intermediate","Deep"],
        default= ["Crustal","Intermediate","Deep"]
    )

    filter_df = filter_df[
        (filter_df["magnitude"].between(mag_range[0],mag_range[1]))&
        (filter_df["depth"].between(deepth_range[0],deepth_range[1]))&
        (filter_df["risk_level"].isin(risk_lavels))&
        (filter_df["tectonic_type"].isin(techtonic_type))
    ]


    st.header("Executive Summary")
    col1,col2,col3,col4,col5 = st.columns(5)
    total_event = len(filter_df)
    critical_event = len(filter_df[filter_df['risk_level']=='Critical'])
    recent_24h = len( filter_df[filter_df['time']>=(filter_df['time'].max()-timedelta(hours=24))])
    avg_meg =  filter_df['magnitude'].mean()
    max_mag =  filter_df['magnitude'].max()
    with st.spinner("loading..."):
        with col1:
            st.metric("Total Events",total_event)
        with col2:
            st.metric("Critical Event",critical_event)
        with col3:
            st.metric("last 24h",recent_24h) 
        with col4:
            st.metric("Average Megnitude",f'{avg_meg:.2f}')
        with col5:
            st.metric("Maximum Megnitude",f'{max_mag:.2f}')   
        # alart system:
        st.markdown("---")
        st.header("Current Alart")
        now = datetime.now()
        recent_event =  filter_df[filter_df['time']>=(now-timedelta(hours=24))]
        alar_df =  recent_event[recent_event["magnitude"]>=4.5].copy()
        alar_df['time_ago'] = (now - alar_df['time']).dt.total_seconds()/3600
        if len(alar_df)>0:
            st.error(f"high risk event in last 24h:{len(alar_df)}")
            for _,rows in alar_df.head(6).iterrows():
                st.warning(f"**M{rows['magnitude']:.1f}** - {rows['place'][:50]} | {rows['time']}")
        else:
            st.success("no highrisk event in last 24h")

    st.markdown("---")
    st.header("Visulaization")  
    col6,col7 = st.columns(2)  

    with col6:
           
    # Count values for each risk level
        
            risk_counts = filter_df['risk_level'].value_counts().reset_index()
           

            fig=px.pie(
                risk_counts,
                names='risk_level',
                values='count',
                title='Risk Level Distribution',
                hole=0,  # change to 0.4 for a donut chart
                color_discrete_sequence=px.colors.qualitative.Safe
            )
            fig.update_traces(textposition='outside', textinfo='label+percent')
            fig.update_layout(height=400, width=400, margin=dict(l=120, r=10, t=60, b=10))
            st.plotly_chart(fig, use_container_width=False)

            hourly = filter_df.groupby('hour').size().reset_index(name='count')

            fig_hour = px.bar(
                 hourly,x='hour',y='count',title="event by hour"
            )
            st.plotly_chart(fig_hour,use_container_width=False)


            st.markdown("---")

            st.header("Risk Map")
            fig_map = px.scatter_mapbox(
                 filter_df,
                 lat = "latitude",
                 lon="longitude",
                 size="magnitude",
                 color="magnitude",
                 color_continuous_scale="Reds",size_max=20,opacity=0.8,
                 hover_name="place",hover_data=["risk_level","depth","time","tectonic_type"],
                 mapbox_style="open-street-map",zoom=3
            )
            fig_map.update_layout(
                 height = 600,
                 margin = dict(r=0,t=113,l=0,b=100)
                 
            )

            st.plotly_chart(fig_map,use_container_width=True)





    with col7:
        # Scatter plot: Magnitude over time
        fig2 = px.scatter(
            filter_df,
            x='time',
            y='magnitude',
            color='risk_level',
            size="magnitude",
            hover_data=['place', 'depth'],
            title="Earthquake Magnitude over Time"
        )

        fig2.update_layout(
            xaxis_title="Time",
            yaxis_title="Magnitude",
            height=400,
            template="plotly_white",
            margin=dict(l=20, r=20, t=70, b=30)
        )
        st.plotly_chart(fig2, use_container_width=False)

        # Daily event count
        daily = filter_df.groupby('date').size().reset_index(name="count")

        fig_daily = px.line(daily, x="date", y="count", title="Daily Rate", markers=True, color="date")
        fig_daily.add_hline(y=daily['count'].mean(), line_dash="dash")

        fig_daily.update_layout(
            margin=dict(l=20, r=20, t=50, b=30)
        )
        st.plotly_chart(fig_daily, use_container_width=False)

        # Aftershock Cluster Section
        st.markdown("---")
        st.header("Aftershock Cluster")

        cluster = filter_df[filter_df["cluster_flag"] == True].copy()

        if len(cluster) > 0:
            st.warning(f"{len(cluster)} events in active clusters (within 24 hours of the previous event)")

            # Assign cluster IDs
            cluster['cluster_id'] = (cluster["hours_since_prev"] > 24).cumsum()

            # Cluster Map Visualization
            fig_cluster = px.scatter_mapbox(
                cluster,
                lat="latitude",
                lon="longitude",
                size="magnitude",
                color="cluster_id",  # Color by cluster
                color_continuous_scale="Oranges",
             
                size_max=25,
                opacity=0.9,
                hover_name="place",
                hover_data={
                    "time": "|%Y-%m-%d %H:%M",
                    "magnitude": ":.2f",
                    "depth": ":.0f",
                    "cluster_id": True
                },
                title="Detected Aftershock Clusters",
                mapbox_style="open-street-map",
                zoom=3
            )

            fig_cluster.update_layout(
                 height = 600,
                 margin = dict(r=0,t=40,l=0,b=173)
               
            )
            st.plotly_chart(fig_cluster, use_container_width=True)
            cluster_summary = cluster.groupby("cluster_id").agg(
                 count = ('magnitude','size'),
                 max_mag = ("magnitude",'max'),
                 center_lat = ("latitude","mean"),
                 center_lon = ("longitude","mean"),
                 start_time = ("time","min")

            ).round(2)
          


            if cluster_summary is not None and not cluster_summary.empty:
                st.subheader("Cluster Summary")
                
                # 1. Sort the DataFrame
                sorted_df = cluster_summary.sort_values('max_mag', ascending=False)

                # 2. Apply styling using the Pandas Styler
                
                # Style A: Deep Color for the Header (Column Names)
                # Target the 'th' (table header) elements.
                styled_df = sorted_df.style.set_table_styles([
                    {'selector': 'th', 'props': [
                        ('background-color', "#0505E4"), # Deep Navy Blue for the header
                        ('color', 'white'),            # White text for contrast
                        ('font-weight', 'bold')
                    ]}
                ])
                
                # Style B: Light Color for the Table Body (Data Cells)
                # Use set_properties() to style all cells (excluding the header).
                styled_df = styled_df.set_properties(**{
                    'background-color': "#7AC6E9", # Very light blue (e.g., pale azure) for the body
                    'color': '#333333',              
                    'border': '1px solid #cccccc'    
                })
                
            # 3. Pass the styled object to st.dataframe
            st.dataframe(styled_df)
            
        else:
            st.success("No active aftershock clusters detected.")

    st.markdown("---")  
    st.header("Decision Support")
    col8,col9 = st.columns(2)
    with col8:
         st.subheader("Recomended Action")
         action = []
         if recent_24h > 10: action.append("Incarese Monitoring Frewuency")
         if critical_event>0: action.append("Isaue publuic sefty alart")
         if len(cluster)>5: action.append("Deploy field assessment team")
         if len(filter_df[filter_df["magnitude"]>=5.5])>3:
              action.append("prepare tsunami erly warning")
         if action:
              for a in action: st.error(a)
         else:
          st.success("No emidiet action required")
    with col9:
         st.subheader("priority Metrics")
         day_span = max(1,(filter_df["date"].max() - filter_df["date"].min()).days)   

         st.metric("Event Rate (/day)",f"{len(filter_df)/day_span:.1f}")    

         st.metric("M>5.0 Event",len(filter_df[filter_df["magnitude"]>5.0])) 

         st.metric("Deep Events(>300)",len(filter_df[filter_df["depth"]>300]))

         st.metric("Active Cluster",len(cluster["cluster_id"].unique()) if len(cluster)>0  else 0)    

    with st.expander("Full dataset And Export"):
         display_cols = ["time","place","magnitude","depth","risk_level","tectonic_type","cluster_flag"]
         st.dataframe(filter_df[display_cols].sort_values('time', ascending=False))

         csv = filter_df[display_cols].to_csv(index=False) 
         st.download_button("Download filtered Data",csv,"filtered_earthquake.csv","text/csv")   
             



            

                            


                
                        
                    



