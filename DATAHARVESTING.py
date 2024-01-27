from googleapiclient.discovery import build
import pymongo
import psycopg2
import pandas as pd
import streamlit as st

#api key connection 
def api_connect():
    api_id="AIzaSyDLysHR5QgdlPA3pSeSBPxdEpco7Ey8z-o"
    api_service_name="youtube"
    api_version="v3"

    youtube=build(api_service_name,api_version,developerKey=api_id)

    return youtube
youtube = api_connect()

#get chanel info
def get_chennel_info(channel_id):
    request=youtube.channels().list(
        part="snippet,contentDetails,statistics",
        id=channel_id
    )
    response=request.execute()
    for i in response["items"]:
        data=dict(channel_name=i["snippet"]["title"],
                channel_id=i["id"],
                subscribers=i["statistics"]["subscriberCount"],
                views=i["statistics"]["viewCount"],
                total_videos=i["statistics"]["videoCount"],
                chennal_discription=i["snippet"]["description"],
                playlist_id=i["contentDetails"]["relatedPlaylists"]["uploads"])
        return data
    


#get vedios Id
def get_videos_ids(channel_id):
    video_ids=[]
    response=youtube.channels().list(id=channel_id,
                                    part="contentDetails").execute()
    playlist_id=response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    next_page_token=None

    while True:
        response1=youtube.playlistItems().list(
                                            part="snippet",
                                            playlistId=playlist_id,
                                            maxResults=50,
                                            pageToken=next_page_token).execute()
        for i in range(len(response1["items"])):
            video_ids.append(response1["items"][i]["snippet"]["resourceId"]["videoId"])

        next_page_token = response1.get("nextPageToken")

        if not next_page_token:
            break
    return video_ids


#get video information
def get_video_info(video_ids):
    video_data=[]
    for video_id in video_ids:
        request=youtube.videos().list(
            part="snippet,contentDetails,statistics",
            id=video_id
        )
        response=request.execute()

        for item in response["items"]:
            data=dict(channel_name=item["snippet"]["channelTitle"],
                    channel_id=item["snippet"]["channelId"],
                    video_id=item["id"],
                    title=item["snippet"]["title"],
                    tags=item["snippet"].get("tags"),
                    thumbnail=item["snippet"]["thumbnails"]["default"]["url"],
                    description=item["snippet"].get("description"),
                    published_date=item["snippet"]["publishedAt"],
                    duration=item["contentDetails"]["duration"],
                    views=item["statistics"].get("viewCount"),
                    likes=item["statistics"].get("likeCount"),
                    comments=item["statistics"].get("commentCount"),
                    favorite_count=item["statistics"]["favoriteCount"],
                    definition=item["contentDetails"]["definition"],
                    caption_status=item["contentDetails"]["caption"]
                    )
            video_data.append(data)
    return video_data

#get comments info
def get_comment_info(video_ids):
    comment_data=[]
    try:
        for video_id in video_ids:
            request=youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=50,
            )
            response=request.execute()

            for item in response["items"]:
                data=dict(comment_id=item["snippet"]["topLevelComment"]["id"],
                        video_Id=item["snippet"]["topLevelComment"]["snippet"]["videoId"],
                        comment_text=item["snippet"]["topLevelComment"]["snippet"]["textDisplay"],
                        comment_author=item["snippet"]["topLevelComment"]["snippet"]["authorDisplayName"],
                        comment_published=item["snippet"]["topLevelComment"]["snippet"]["publishedAt"],
                        )
                comment_data.append(data)
    except:
        pass
    return comment_data

#get_playlist_details

def get_playlist_details(channel_id):
        next_page_token=None
        All_data=[]
        while True:
                request=youtube.playlists().list(
                        part="snippet,contentDetails",
                        channelId=channel_id,
                        maxResults=50,
                        pageToken=next_page_token)  
                response=request.execute()

                for item in response["items"]:
                        data=dict(playlist_id=item["id"],
                                Title=item["snippet"]["title"],
                                channel_id=item["snippet"]["channelId"],
                                channel_name=item["snippet"]["channelTitle"],
                                publishedAt=item["snippet"]["publishedAt"],
                                video_count=item["contentDetails"]["itemCount"])
                        All_data.append(data)
                next_page_token = response.get("nextPageToken")
                
                if next_page_token is None:
                        break
        return All_data

#upload to mongodb
client=pymongo.MongoClient("mongodb+srv://rakeshashwanth:Rakeshb@rakesh.mnuqcoi.mongodb.net/?retryWrites=true&w=majority")
db=client["youtube_data"]

def channel_details(channel_id):
    ch_details=get_chennel_info(channel_id)
    pl_details=get_playlist_details(channel_id)
    vi_ids=get_videos_ids(channel_id)
    vi_details=get_video_info(vi_ids)
    com_details=get_comment_info(vi_ids)

    coll1=db["channel_details"]
    coll1.insert_one({"channel_information":ch_details,"playlist_information":pl_details,
                     "video_information":vi_details,"comment_information":com_details})
    return "uploaded successfully"
    
    

#table creation for channels,playlist,videos,comments.
def channels_table():
    mydb=psycopg2.connect(host="localhost",
                        user="postgres",
                        password="rakeshb",
                        database="youtube_data",
                        port="5432")
    cursor=mydb.cursor()

    drop_query='''drop table if exists channels'''
    cursor.execute(drop_query)
    mydb.commit()


    try:
        create_query='''create table if not exists channels(channel_name varchar(100),
                                                            channel_id varchar(100) primary key,
                                                            subscribers bigint,
                                                            views bigint,
                                                            total_videos int,
                                                            chennal_discription text,
                                                            playlist_id varchar(80))'''
        cursor.execute(create_query)
        mydb.commit()
    except:
        print("channels table already created")

    ch_list=[]
    db=client["youtube_data"]
    coll1=db["channel_details"]
    for ch_data in coll1.find({}, {"_id":0,"channel_information":1}):
        ch_list.append(ch_data["channel_information"])
    df=pd.DataFrame(ch_list)


    for index,row in df.iterrows():
        insert_query= '''insert into channels(channel_name,
                                            channel_id,
                                            subscribers,
                                            views,
                                            total_videos,
                                            chennal_discription,
                                            playlist_id)
                                            
                                            values(%s,%s,%s,%s,%s,%s,%s)'''
        values=(row["channel_name"],
                row["channel_id"],
                row["subscribers"],
                row["views"],
                row["total_videos"],
                row["chennal_discription"],
                row["playlist_id"])
        try:
            cursor.execute(insert_query,values)
            mydb.commit()

        except:
            print("channel value already inserted")


def playlist_table():

    mydb=psycopg2.connect(host="localhost",
                        user="postgres",
                        password="rakeshb",
                        database="youtube_data",
                        port="5432")
    cursor=mydb.cursor()

    drop_query='''drop table if exists playlists'''
    cursor.execute(drop_query)
    mydb.commit()



    create_query='''create table if not exists playlists(playlist_id varchar(100) primary key,
                                                        Title varchar(100),
                                                        channel_id varchar(100),
                                                        channel_name varchar(100),
                                                        publishedAt timestamp,
                                                        video_count int)'''

    cursor.execute(create_query)
    mydb.commit()

    pl_list=[]
    db=client["youtube_data"]
    coll1=db["channel_details"]
    for pl_data in coll1.find({}, {"_id":0,"playlist_information":1}):
        for i in range(len(pl_data["playlist_information"])):
            pl_list.append(pl_data["playlist_information"][i])
    df1=pd.DataFrame(pl_list)

    for index,row in df1.iterrows():
        insert_query= '''insert into playlists(playlist_id,
                                            Title,
                                            channel_id,
                                            channel_name,
                                            publishedAt,
                                            video_count)

                                            values(%s,%s,%s,%s,%s,%s)'''
        


        values=(row["playlist_id"],
                row["Title"],
                row["channel_id"],
                row["channel_name"],
                row["publishedAt"],
                row["video_count"])
    
        cursor.execute(insert_query,values)
        mydb.commit()


def videos_table():
        mydb=psycopg2.connect(host="localhost",
                        user="postgres",
                        password="rakeshb",
                        database="youtube_data",
                        port="5432")
        cursor=mydb.cursor()

        drop_query='''drop table if exists videos'''
        cursor.execute(drop_query)
        mydb.commit()



        create_query='''create table if not exists videos(channel_name varchar(100),
                                                        channel_id varchar(100),
                                                        video_id varchar(30) primary key,
                                                        title varchar(150),
                                                        tags text,
                                                        thumbnail varchar(200),
                                                        description text,
                                                        published_date timestamp,
                                                        duration interval,
                                                        views bigint,
                                                        likes bigint,
                                                        comments int,
                                                        favorite_count int,
                                                        definition varchar(10),
                                                        caption_status varchar(50)
                                                        )'''

        cursor.execute(create_query)
        mydb.commit()


        vi_list=[]
        db=client["youtube_data"]
        coll1=db["channel_details"]
        for vi_data in coll1.find({}, {"_id":0,"video_information":1}):
                for i in range(len(vi_data["video_information"])):
                        vi_list.append(vi_data["video_information"][i])
        df2=pd.DataFrame(vi_list)


        for index,row in df2.iterrows():
                insert_query= '''insert into videos(channel_name,
                                                                channel_id,
                                                                video_id,
                                                                title,
                                                                tags,
                                                                thumbnail,
                                                                description,
                                                                published_date,
                                                                duration,
                                                                views,
                                                                likes,
                                                                comments,
                                                                favorite_count,
                                                                definition,
                                                                caption_status)

                                                        values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'''



                values=(row["channel_name"],
                        row["channel_id"],
                        row["video_id"],
                        row["title"],
                        row["tags"],
                        row["thumbnail"],
                        row["description"],
                        row["published_date"],
                        row["duration"],
                        row["views"],
                        row["likes"],
                        row["comments"],
                        row["favorite_count"],
                        row["definition"],
                        row["caption_status"],           
                        )

                cursor.execute(insert_query,values)
                mydb.commit()


def comments_table():
        mydb=psycopg2.connect(host="localhost",
                        user="postgres",
                        password="rakeshb",
                        database="youtube_data",
                        port="5432")
        cursor=mydb.cursor()

        drop_query='''drop table if exists comments'''
        cursor.execute(drop_query)
        mydb.commit()



        create_query='''create table if not exists comments(comment_id varchar(100) primary key,
                                                        video_Id varchar(50),
                                                        comment_text text,
                                                        comment_author varchar(150),
                                                        comment_published timestamp)'''

        cursor.execute(create_query)
        mydb.commit()

        com_list=[]
        db=client["youtube_data"]
        coll1=db["channel_details"]
        for com_data in coll1.find({}, {"_id":0,"comment_information":1}):
                for i in range(len(com_data["comment_information"])):
                        com_list.append(com_data["comment_information"][i])
        df3=pd.DataFrame(com_list)

        for index,row in df3.iterrows():
                insert_query= '''insert into comments(comment_id,
                                                        video_Id,
                                                        comment_text,
                                                        comment_author,
                                                        comment_published)

                                                values(%s,%s,%s,%s,%s)'''
                




                values=(row["comment_id"],
                        row["video_Id"],
                        row["comment_text"],
                        row["comment_author"],
                        row["comment_published"]
                        )
        
                cursor.execute(insert_query,values)
                mydb.commit()


def tables():
    channels_table()
    playlist_table()
    videos_table()
    comments_table()

    return "Table Created Sucessfully"

def show_channels_table():
    ch_list=[]
    db=client["youtube_data"]
    coll1=db["channel_details"]
    for ch_data in coll1.find({}, {"_id":0,"channel_information":1}):
        ch_list.append(ch_data["channel_information"])
    df=st.dataframe(ch_list)

    return df

def show_playlists_table():
    pl_list=[]
    db=client["youtube_data"]
    coll1=db["channel_details"]
    for pl_data in coll1.find({}, {"_id":0,"playlist_information":1}):
        for i in range(len(pl_data["playlist_information"])):
            pl_list.append(pl_data["playlist_information"][i])
    df1=st.dataframe(pl_list)

    return df1

def show_videos_table():
    vi_list=[]
    db=client["youtube_data"]
    coll1=db["channel_details"]
    for vi_data in coll1.find({}, {"_id":0,"video_information":1}):
            for i in range(len(vi_data["video_information"])):
                    vi_list.append(vi_data["video_information"][i])
    df2=st.dataframe(vi_list)

    return df2

def show_comments_table():
    com_list=[]
    db=client["youtube_data"]
    coll1=db["channel_details"]
    for com_data in coll1.find({}, {"_id":0,"comment_information":1}):
            for i in range(len(com_data["comment_information"])):
                    com_list.append(com_data["comment_information"][i])
    df3=st.dataframe(com_list)

    return df3

#streamlit part

with st.sidebar:
    st.title(":red[YOUTUBE DATA HARVESTING AND WAREHOUSING]")
    st.header("Skill Take Away")
    st.caption("_python Scripting_")
    st.caption("_Data Collection_")
    st.caption("_MongoDB_")
    st.caption("_API Integration_")
    st.caption("_Data Management using MongoDB and SQL_")

channel_id=st.text_input("Enter the Channel ID")

if st.button("Collect and Store Data"):
    ch_ids=[]
    db=client["youtube_data"]
    coll1=db["channel_details"]
    for ch_data in coll1.find({},{"_id":0,"channel_information":1}):
        ch_ids.append(ch_data["channel_information"]["channel_id"])

    if channel_id in ch_ids:
        st.success("channel_details of the given channel id alreary exists")
    
    else:
        insert=channel_details(channel_id)
        st.success(insert)

if st.button("Migrate to Sql"):
    Table=tables

show_table=st.radio("SELECT THE TABLE FOR VIEW",("CHANNELS","PLAYLIST","VIDEOS","COMMENTS"))

if show_table=="CHANNELS":
    show_channels_table()

elif show_table=="PLAYLISTS":
    show_playlists_table()

elif show_table=="VIDEOS":
    show_videos_table()

elif show_table=="COMMENTS":
    show_comments_table()


# Sql connection

mydb=psycopg2.connect(host="localhost",
                    user="postgres",
                    password="rakeshb",
                    database="youtube_data",
                    port="5432")
cursor=mydb.cursor()

question=st.selectbox("Select yout question",("1. All the videos and the channek name",
                                              "2. channels with most number of videos",
                                              "3. 10 most viewed videos",
                                              "4. comments in each videos",
                                              "5. videos with highest likes",
                                              "6. likes of all videos",
                                              "7. views of each channel",
                                              "8. videos publised in the year of 2022",
                                              "9. average duration of all videos in each channel",
                                              "10. videos with highest number of comments"))

if question=="1. All the videos and the channek name":
    query1='''select title as videos, channel_name as channelname from videos'''
    cursor.execute(query1)
    mydb.commit()
    t1=cursor.fetchall()
    df=pd.DataFrame(t1,columns=["video title","channel name"])
    st.write(df)

elif question=="2. channels with most number of videos":
    query2='''select channel_name as channelname, total_videos as no_videos from channels 
                order by total_videos desc'''
    cursor.execute(query2)
    mydb.commit()
    t2=cursor.fetchall()
    df2=pd.DataFrame(t2,columns=["channel name","No of videos"])
    st.write(df2)

elif question=="3. 10 most viewed videos":
    query3='''select views as views, channel_name as channelname, title as videotitle from videos 
                where views is not null order by views desc limit 10'''
    cursor.execute(query3)
    mydb.commit()
    t3=cursor.fetchall()
    df3=pd.DataFrame(t3,columns=["views","channel name","videotitle"])
    st.write(df3)

elif question=="4. comments in each videos":
    query4='''select comments as no_comments,title as videotitle from videos where comments is not null'''
    cursor.execute(query4)
    mydb.commit()
    t4=cursor.fetchall()
    df4=pd.DataFrame(t4,columns=["no of comments","videotitle"])
    st.write(df4)

elif question=="5. videos with highest likes":
    query5='''select title as video_title, channel_name as channelname, likes as likecount
                from videos where likes is not null order by likes desc'''
    cursor.execute(query5)
    mydb.commit()
    t5=cursor.fetchall()
    df5=pd.DataFrame(t5,columns=["videotitle","channelname","likecount"])
    st.write(df5)

elif question=="6. likes of all videos":
    query6='''select likes as likecount, title as videotitle from videos'''
    cursor.execute(query6)
    mydb.commit()
    t6=cursor.fetchall()
    df6=pd.DataFrame(t6,columns=["likecount","videotitle"])  
    st.write(df6)

elif question=="7. views of each channel":
    query7='''select channel_name as channelname, views as totalviews from channels'''
    cursor.execute(query7)
    mydb.commit()
    t7=cursor.fetchall()
    df7=pd.DataFrame(t7,columns=["channelname","totalviews"])
    st.write(df7)

elif question=="8. videos publised in the year of 2022":
    query8='''select title as video_title,published_date as videorelease, channel_name as channelname from videos 
                where extract(year from published_date)=2022'''
    cursor.execute(query8)
    mydb.commit()
    t8=cursor.fetchall()
    df8=pd.DataFrame(t8,columns=["videotitle","published_date","channelname"])
    st.write(df8)

elif question=="9. average duration of all videos in each channel":
    query9='''select channel_name as channelname, AVG(duration) as averageduration from videos group by channel_name'''
    cursor.execute(query9)
    mydb.commit()
    t9=cursor.fetchall()
    df9=pd.DataFrame(t9,columns=["channelname","averageduration"])
    T9=[]
    for index,row in df9.iterrows():
        channel_title=row["channelname"]
        average_duration=row["averageduration"]
        average_duration_str=str(average_duration)
        T9.append(dict(channeltitle=channel_title,avgduration=average_duration_str))
    df1=pd.DataFrame(T9)
    st.write(df1)

elif question=="10. videos with highest number of comments":
    query10='''select title as videostitle, channel_name as channelname, comments as comments from videos
                where comments is not null order by comments desc'''
    cursor.execute(query10)
    mydb.commit()
    t10=cursor.fetchall()
    df10=pd.DataFrame(t10,columns=["video title","channel name","comments"])
    st.write(df10)

