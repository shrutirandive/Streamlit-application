import pandas as pd
import streamlit as st
import json
from pandas import json_normalize
import plotly.express as px
import datetime
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import plotly.io as pio
from time import strftime, localtime
import os
import io
import openpyxl

# storing all health metrics in dictionary
dict_metrics = {'Heart Rate Quality':'hr_quality', 'Temperature':'temperature', 'Activity':'activity', 
                'Galvanic Skin Response':'gsr', 'Steps':'steps', 'Battery':'battery', 'Spo2': 'spo2',
                'Heart Rate': 'bpm', 'Heart Rate Count': 'hr_count', 'Adjusted GSR': 'adjusted_gsr', 'Act Type': 'act_type',
                'Sleep':'sleep', 'Emotion':'emotion'}

# Dictionary for type11
type11 = {
    'Heart Rate Quality': 'hr_quality',
    'Temperature': 'temperature',
    'Activity': 'activity',
    'Galvanic Skin Response': 'gsr',
    'Steps': 'steps',
    'Battery': 'battery',
    'Heart Rate': 'bpm',
    'Heart Rate Count': 'hr_count',
    'Adjusted GSR': 'adjusted_gsr',
    'Act Type': 'act_type',
    }

# Dictionary for type12
type12= {
    'Steps': 'steps',
    'Activity': 'activity',
    'Act Type': 'act_type',
    'Battery': 'battery'
}

# Dictionary for type74
type74= {
    'Heart Rate Count': 'hr_count',
    'Adjusted GSR': 'adjusted_gsr',
    'Spo2': 'spo2'
}

# Dictionary for type_derived
type_derived= {
    'Sleep': 'sleep',
    'Emotion': 'emotion'
}

def import_data_from_json(file_path):
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            return data
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
    except json.JSONDecodeError:
        print(f"Error: Unable to parse JSON from '{file_path}'. Check if the file contains valid JSON data.")
    return None

def categorize_hour(hour):
    '''Function to categorize hours into morning, afternoon, evening, night'''
    if 6 <= hour < 12:
        return 'Morning'
    elif 12 <= hour < 18:
        return 'Afternoon'
    elif 18 <= hour < 24:
        return 'Evening'
    else:
        return 'Night'

def categorize_act_type(act_type):
    '''Function to categorize act_type'''
    if act_type==0.0:
        return 'Idle'
    elif act_type==1.0:
        return 'Walking'
    elif act_type==2.0:
        return 'Running'
    elif act_type==3.0:
        return 'Unknown'
    else:
        return 'Offwrist'

def combine_dataframes(dfs):
    if dfs:
        combined_df = pd.concat(dfs, ignore_index=True)
        return combined_df
    return None

def create_metrics_df(data, metrics):
    if isinstance(metrics, str): 
        # Convert it to a list with a single element
        metrics = [metrics]  

    merged_df = pd.DataFrame()  
    for metric in metrics:
        json_keys = data['data'][0].keys()
        # check if metrics is present in given json file 
        if metric in json_keys:
            metric_data = data['data'][0][metric]

            metric_df = pd.DataFrame.from_dict(metric_data[0], orient='index', columns=[metric])
            metric_df.reset_index(inplace=True)
            metric_df.rename(columns={'index': 'timestamp'}, inplace=True)
            if merged_df.empty:
                # If it's the first metric, assign it directly to the merged DataFrame
                merged_df = metric_df  
            else:
                # Merge the metric DataFrame with the existing merged DataFrame based on the 'timestamp' column
                merged_df = pd.merge(merged_df, metric_df, how="outer", on='timestamp', suffixes=('', ''))
                merged_df = merged_df.fillna(0.0)
        else:
            pass
    # merged_df['timestamp'] = merged_df['timestamp'].astype(float)

    merged_df['date_time'] = pd.to_datetime(merged_df['timestamp'], unit='s')  
    merged_df['date'] = merged_df['date_time'].dt.date
    print(merged_df.dtypes)
    # Add a 'weekday' column by formatting 'date_time' to display the weekday name
    merged_df['weekday'] = merged_df['date_time'].dt.strftime("%A")
    merged_df['hour'] = merged_df['date_time'].dt.hour
    merged_df['time_range'] = merged_df['hour'].apply(categorize_hour)
    if 'act_type' in merged_df:
        merged_df['categorize_act_type'] = merged_df['act_type'].apply(categorize_act_type)
    
    print(merged_df)

    # Set 'date_time' as the index
    # merged_df = merged_df.set_index('date_time')
    print(merged_df)
    return merged_df

def fetch_and_combine_child_data(child_id, directory):
    child_files = [file for file in os.listdir(directory) if child_id in file and file.endswith('.json')]
    dataframes = []

    for file_name in child_files:
        file_path = os.path.join(directory, file_name)
        data = import_data_from_json(file_path)
        if data is not None:
            df = create_metrics_df(data, metrics=dict_metrics.values())
            if df is not None:
                dataframes.append(df)

    combined_df = combine_dataframes(dataframes)
    return combined_df

def streamlit(child_id, directory):
    try: 
        with open('design.css') as design:
            st.markdown(f'<style>{design.read()}</style>', unsafe_allow_html=True)
        
        st.markdown("""<link rel="preconnect" href="https://fonts.googleapis.com">
            <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
            <link href="https://fonts.googleapis.com/css2?family=Alata&display=swap" rel="stylesheet">""", unsafe_allow_html=True)
        
        # Creating dataframe for Health metrics
        df = fetch_and_combine_child_data(child_id, directory)
        print("=================DF=================")
        print(df)     
        ChildIdKPI = f"<h3 style='color:#e60039; font-size: 25px;'>Child Id: {child_id}</h3>"
        st.sidebar.markdown(ChildIdKPI, unsafe_allow_html=True)       
        
        if len(df)!=0:

            start = df['date_time'].iloc[0]
            end = df['date_time'].iloc[-1]
            st.sidebar.markdown(f"<h3 style='color:#005170'; font-size:55px;>Data recorded from {start} to {end}</h3>", unsafe_allow_html=True)

            #  Type of health Metrics
            st.sidebar.markdown("<h3 style=color:#e60039;>Select Type:</h3>", unsafe_allow_html=True)
            option_type = st.sidebar.multiselect('type', ('type11', 'type12', 'type74', 'type_derived'), default='type11', label_visibility='collapsed')

            st.sidebar.markdown("<h3 style=color:#e60039;>Select Date and Time :</h3>", unsafe_allow_html=True)
            startdate = st.sidebar.date_input("Start Date:", datetime.date(start.year, start.month, start.day))
            starttime = st.sidebar.time_input("Start Time:", datetime.time(start.hour, start.minute))
            enddate = st.sidebar.date_input("End Date:", datetime.date(end.year, end.month, end.day))
            endtime = st.sidebar.time_input("End Time:", datetime.time(end.hour, end.minute))

            # Convert start and end date/time strings to datetime objects for creating a separate dataframe based on the time range selected
            start_selected = pd.to_datetime(str(startdate) + ' ' + str(starttime), format='%Y-%m-%d %H:%M:%S', errors='coerce')
            end_selected = pd.to_datetime(str(enddate) + ' ' + str(endtime), format='%Y-%m-%d %H:%M:%S', errors='coerce')
            print(start_selected, start)
            if (start_selected < start) or (end_selected > end):
                st.markdown(f"Selected Start DateTime: `{start_selected}`\nEnd DateTime: `{end_selected}`")
                st.markdown(f"Please select DateTime from `{start}` and `{end}`", unsafe_allow_html=True)         
            else:
                # create dictionary for adding all metrics based on option type selected 
                selected_metrics = {}
                for m_type in option_type:
                    print(m_type)
                    metrics = eval(m_type)
                    selected_metrics.update(metrics)
                print(option_type)
                print(selected_metrics.values())

                # creating df to store all the metrics data from the main df
                new_df = df.set_index('date_time')
                new_df = new_df[(new_df.index>start_selected) & (new_df.index<end_selected)]
                print("============== NEW DF ==============")
                print(new_df)
                print(start_selected, end_selected)
                
                print("====================================")
                
                # Metrics
                a1,a2,a3,a4 = st.columns(4)
                b1,b2,b3,b4 = st.columns(4)
                # df = df[(df.index>=start_selected) & (df.index<=end_selected)]

                if 'steps' in df:
                    step_count = new_df['steps'].sum()
                else:
                    step_count = 0
                a1.metric("TOTAL STEP COUNT", step_count, "steps")

                if 'gsr' in df:
                    avg_gsr = round(new_df['gsr'].mean(), 2)
                else:
                    avg_gsr = 0
                a2.metric("GSR", avg_gsr, "mS")

                if 'temperature' in df:
                    avg_temp = round(new_df['temperature'].mean(), 2)
                else:
                    avg_temp = 0
                a3.metric("TEMPERATURE", avg_temp, "^Celcius")

                if 'bpm' in df:
                    bpm = round(new_df['bpm'].mean(), 2)
                else:
                    bpm = 0
                a4.metric("HEART RATE ", bpm, "BPM")

                if 'hr_quality' in df:
                    hr = round(new_df['hr_quality'].mean(), 2)
                else:
                    hr = 0
                b1.metric("HEART RATE QUALITY", hr, "BPM")

                if 'activity' in df:
                    activity = round(new_df['activity'].mean(), 2)
                else:
                    activity = 0
                b2.metric("ACTIVITY", activity, "activity")

                if 'spo2' in df:
                    spo2 = round(new_df['spo2'].mean(), 2)
                else:
                    spo2 = 0
                b3.metric("SPO2", spo2, "%")

                if 'battery' in df:
                    battery = round(new_df['battery'].mean(), 2)
                else:
                    battery = 0
                b4.metric("BATTERY", battery, "%")
                            
                # Health metrics Breakdown by ACT Type
                st.subheader("Scatter Plot")
                sp_key = st.selectbox('Select Y Variable over Time', selected_metrics.keys())
                sp_value = dict_metrics[sp_key]
                print(sp_key, sp_value)
                if sp_value in new_df:
                    # Create the scatter plot using Plotly Express
                    scatter_plot = px.scatter(new_df, x=new_df.index, y=sp_value, color='categorize_act_type',
                                            title=f'Scatter Plot of {sp_key} Over Time',
                                            labels={'act_type': 'Act Type'}, color_continuous_scale='Inferno',color_discrete_sequence=[
                                                    "#0068c9","#83c9ff","#ff2b2b","#ffabab","#29b09d","#7defa1","#ff8700","#ffd16a","#6d3fc0","#d5dae5",],
                                            )

                    st.plotly_chart(scatter_plot, use_container_width=True)
                    download_charts(scatter_plot, f'scatter_plot_{child_id}.html')
                else:
                    st.write(f"{sp_key} data is not recorded for this device")

                # BoxPlot
                st.subheader("Box Plot")
                # Health metrics Distribution by WeekDay
                keyboxplot = "keyboxplot"
                bp_key = st.selectbox('Select Y Variable over Time', selected_metrics.keys(), key=keyboxplot)
                bp_value = dict_metrics[bp_key]
                print(bp_key, bp_value)
                if bp_value in new_df:
                    box_plot = px.box(new_df, x='weekday', y=bp_value, title=f'{bp_key} Box Plot',
                            labels={bp_value: bp_key},
                            color_discrete_sequence=[
                                "#0068c9", "#83c9ff", "#ff2b2b", "#ffabab", "#29b09d", "#7defa1",
                                "#ff8700", "#ffd16a", "#6d3fc0", "#d5dae5"
                            ])
                    st.plotly_chart(box_plot, use_container_width=True)
                    download_charts(box_plot, f'bar_chart_{child_id}.html')

                else:
                    st.write(f"{bp_key} data is not recorded for this device")

                # Histogram
                dict_bins = None
                # Define bin ranges dynamically using try-except block
                dict_bins = {'hr_quality': None, 'temperature': [20, 25, 30, 35], 'activity': None,
                            'gsr': None, 'steps': [0, 20, 40, 60, 80, 100], 'battery': None, 'spo2': None,
                            'heartrate': None, 'hr_count': None, 'adjusted_gsr': 'adjusted_gsr_bins', 'act_type': [0,1,2,3,4]}
            
                st.subheader(f"Histogram")
                selectbox_key = "key1"
                h_key = st.selectbox('Select Y Variable over Time', selected_metrics.keys(), key=selectbox_key)
                h_value = dict_metrics[h_key]

                try:
                    if h_value in new_df:
                        dict_bins[h_value] = [new_df[h_value].min(), new_df[h_value].mean(), new_df[h_value].max()]
                    else:
                        st.write(f"{h_key} data is not recorded for this device")
                except KeyError:
                    st.write(f"{h_key} data is not recorded for this device")

                if dict_bins[h_value] is not None:
                    histogram = px.histogram(new_df, x=h_value, nbins=len(dict_bins[h_value]), 
                                            range_x=[dict_bins[h_value][0], dict_bins[h_value][-1]], 
                                            title=f'{h_key} Histogram', labels={h_value: h_key}, text_auto=True,
                                            color_discrete_sequence=[
                                                    "#0068c9","#83c9ff","#ff2b2b","#ffabab","#29b09d","#7defa1","#ff8700","#ffd16a","#6d3fc0","#d5dae5",],
                                            )
                    st.plotly_chart(histogram, use_container_width=True)
                    download_charts(histogram, f'histogram_{child_id}.html')

                
                # Pie Chart
                st.subheader("Proportion of Activity Types")
                pie_chart = px.pie(new_df, names='categorize_act_type')
                st.plotly_chart(pie_chart, use_container_width=True)

                # Line Chart
                st.subheader("Line Chart")
                lc_key = st.multiselect(f'Select Y Variable over Time', selected_metrics.keys())
                line_chart = make_subplots(rows=len(lc_key)+1, cols=1, vertical_spacing=0.2, shared_xaxes=True,
                                        )
                for i, metric in enumerate(lc_key):
                    y_column = dict_metrics[metric]
                    if y_column in new_df:
                        line_chart.append_trace(go.Scatter(x=new_df.index, y=new_df[y_column], name=metric, mode='lines+markers'), row=i+1, col=1)
                    else:
                        st.write(f"{metric} data is not recorded for this device")
                line_chart.update_layout(height=750, width=700)
                st.plotly_chart(line_chart, use_container_width=True)
        else:
            st.write("Data is not recorded")

    except Exception as e:
        st.write(f"Error: {e}")

def download_charts(fig, filename):
    buffer = io.StringIO()
    fig.write_html(buffer, include_plotlyjs='cdn')
    html_bytes = buffer.getvalue().encode()
    print(child_id)
    st.download_button(
        label='Download Chart',
        data=html_bytes,
        file_name=filename,
        mime='text/html'
    )

if __name__ == '__main__':
    st.set_page_config(page_title="Kiddo", layout="wide")
    st.title(":bar_chart: Kiddo Health Dashboard")

    child_id = st.text_input('Enter Child Id: ','63d816888d4d9b473b3f2a5e')  
    data_directory = st.text_input('Enter Directory Path: ')  
    if data_directory:
        combined_dataframe = fetch_and_combine_child_data(child_id, data_directory)
        streamlit(child_id, data_directory)
    else:
        st.markdown("Please mention the directory path to fetch data for given child id")
