from flask import Flask,render_template_string
from flask import render_template
from flask import request
from flask import redirect
from flask import url_for
from flask import session
import datetime
import re
import time
from datetime import datetime
from datetime import timedelta, date
from datetime import timedelta, date
# from dateutil.relativedelta import relativedelta
from dateutil.relativedelta import relativedelta
from flask import flash
import math


import mysql.connector
from mysql.connector import FieldType
import connect


app = Flask(__name__)
app.secret_key = "admin123"
dbconn = None
connection = None

def getCursor():
    global dbconn
    global connection
    connection = mysql.connector.connect(user=connect.dbuser, \
    password=connect.dbpass, host=connect.dbhost, \
    database=connect.dbname, autocommit=True)
    dbconn = connection.cursor()
    return dbconn


# public interface
@app.route("/")
def home():
    if "username" in session:
        userID = session["userID"]
        cur=getCursor()
        cur.execute("SELECT * FROM role WHERE role='member'")
        memberIDList = []
        memberIDs = cur.fetchall()
        for memberID in memberIDs:
            memberIDList.append(memberID[0])
        if userID in memberIDList:
            username = session["username"]
            return render_template("base.html", username=username)
        else:
            session.pop("username", None)
            return redirect(url_for("home"))
    else:
        return render_template("base.html")


@app.route("/membership/mySubscription")
def mySubscription():  
    if "username" in session:
        username = session["username"]
        cur = getCursor()
        cur.execute("SELECT * FROM Member where Member.Email=%s",(username,))
        select_result_MemberInfo = cur.fetchone()
        MemberID=select_result_MemberInfo[0]
        AutoFee=select_result_MemberInfo[-6]
        MemberStatus=select_result_MemberInfo[-2]
        cur = getCursor()
        cur.execute("""select distinct max(SubscriptionEndDate) from subscription 
                    where memberID=%s""",(MemberID,))
        select_result_SubscriptionInfo=cur.fetchone()
        ExpiryDate=select_result_SubscriptionInfo[0]
        # if expiry date is not empty
        Today=date.today()
        #if ExpiryDate equals to none means the member never had subscription records.Tell him to contact manager.
        if ExpiryDate!=None:
            if ExpiryDate>=Today and AutoFee=='No':
                daystoExpiry=abs(ExpiryDate-Today).days
                # cur.execute( """UPDATE Member SET AuthorityOnCollectingFees ="No"
                # where MemberID=%s """,(MemberID,))
                validperiodNotice=f" Your subscription status will become inactive on {ExpiryDate}."
                daysRemain=f"Your current subscription still has a validity of {daystoExpiry} days and you will not be auto charged for the next month"
                return render_template("mySubscription.html", 
                                username=username, 
                                select_result=select_result_MemberInfo ,
                                validperiodNotice=validperiodNotice,
                                daysRemain=daysRemain)
                                    
            elif ExpiryDate>=Today and AutoFee=='Yes':
                DeductionNotice=f"You subscription will be auto renewed on {ExpiryDate}."
                return render_template("mySubscription.html", 
                            username=username, 
                            select_result=select_result_MemberInfo ,
                            DeductionNotice=DeductionNotice)
            elif ExpiryDate<Today:
                ExpiryNotice=f" Your account has expired on {ExpiryDate}." 
                return render_template("mySubscription.html", 
                            username=username, 
                            select_result=select_result_MemberInfo ,
                            ExpiryNotice=ExpiryNotice,ExpiryDate=ExpiryDate,
                            MemberStatus=MemberStatus)
                # cur = getCursor()
                # cur.execute( """UPDATE Member SET MemberStatus = 'Inactive',AuthorityOnCollectingFees ="No"
                #             where MemberID=%s """,(MemberID,))
                # print("aha")
    #if the select_result_SubscriptionInfo[0] is empty.Means the subscription is ongoing valid so no end date.
        else:
            if MemberStatus=='Inactive':
                flash("You have never activated a subscription before. Please contact the manager to activate your first subscription.","ContactManager")
                return redirect('/membership')
       

    else:
        return redirect(url_for("home")) 
      
      
        
@app.route("/membership/CancelSubscription",methods=['POST'])
def CancelSubscription():
    if "username" in session:
        username = session["username"]
        MemberID=request.form["MemberID"]
        TaskToDo=request.form['TaskToDo']
        cur=getCursor()
        cur.execute( """select * from Member 
                        where MemberID=%s """,(MemberID,))
        dbrsultSubscriptionInfo=cur.fetchall()
        cur = getCursor()
        cur.execute("""select distinct max(SubscriptionEndDate) from subscription 
                where memberID=%s""",(MemberID,))
        select_result_SubscriptionInfo=cur.fetchone()
        ExpiryDate=select_result_SubscriptionInfo[0]
        Today=date.today()
        # # 计算相差的天数
        delta = ExpiryDate - Today
            
        if TaskToDo=='Deactivate':
            #关闭自动扣费
            cur = getCursor()
            cur.execute( """UPDATE Member SET AuthorityOnCollectingFees ="No"
                        where MemberID=%s """,(MemberID,))
            flash("You have successfully cancelled the Auto-renew for your subscription!","cancelSubSuccess")
 
        elif TaskToDo=='Reactivate': 
            cur = getCursor()
            cur.execute( """UPDATE Member SET MemberStatus = 'Active', AuthorityOnCollectingFees ="Yes"
                            where MemberID=%s """,(MemberID,))
            if ExpiryDate<Today:
                # get new expiry date
                NewExpiryDate = Today + relativedelta(months=1)        
                #insert new subscription data into db
                cur.execute( """INSERT INTO Subscription (MemberID, SubscriptionStartDate, SubscriptionEndDate, PaymentAmount, IsPaid)
                                VALUES(%s,%s,%s,100,1)""",(MemberID,Today,NewExpiryDate))

            flash("You have successfully reactivated the auto-renew for your subscription!","ReActSuccess")

        return redirect("/membership/mySubscription")
    else:
        return render_template("membership.html")



    
@app.route("/classes")
def classes():
    if "username" in session:
        username = session["username"]
    else:
        username=''
    #get user input date info
    dateChosen=request.args.get("dateChosen","")
    #if user input is empty,show current date class schedule
    #min date(today)
    Today=date.today()
    #max date
    three_weeks = timedelta(weeks=3)
    maxdate = Today + three_weeks
    if dateChosen=="" : 
        dateChosen=Today
        WeekNum=Today.strftime("%W")
    else:
        dateChosen=datetime.strptime(dateChosen, '%Y-%m-%d').date()
        WeekNum=int(dateChosen.strftime("%W"))
    WeekNum=f"{WeekNum}%"
    #get date
    cur=getCursor() 
    cur.execute("""SELECT DISTINCT 
                    'Date' AS StartTime,
                    DATE_FORMAT(MAX(CASE WHEN WeekDayTable.WeekDay = 'Monday' THEN WeekDayTable.ClassDate ELSE '' END), '%d-%b-%Y') AS Monday,
                    DATE_FORMAT(MAX(CASE WHEN WeekDayTable.WeekDay = 'Tuesday' THEN WeekDayTable.ClassDate ELSE '' END), '%d-%b-%Y') AS Tuesday,
                    DATE_FORMAT(MAX(CASE WHEN WeekDayTable.WeekDay = 'Wednesday' THEN WeekDayTable.ClassDate ELSE '' END), '%d-%b-%Y') AS Wednesday,
                    DATE_FORMAT(MAX(CASE WHEN WeekDayTable.WeekDay = 'Thursday' THEN WeekDayTable.ClassDate ELSE '' END), '%d-%b-%Y') AS Thursday,
                    DATE_FORMAT(MAX(CASE WHEN WeekDayTable.WeekDay = 'Friday' THEN WeekDayTable.ClassDate ELSE '' END), '%d-%b-%Y') AS Friday,
                    DATE_FORMAT(MAX(CASE WHEN WeekDayTable.WeekDay = 'Saturday' THEN WeekDayTable.ClassDate ELSE '' END), '%d-%b-%Y') AS Saturday,
                    DATE_FORMAT(MAX(CASE WHEN WeekDayTable.WeekDay = 'Sunday' THEN WeekDayTable.ClassDate ELSE '' END), '%d-%b-%Y') AS Sunday
                    FROM (SELECT ClassID,ClassDate, DATE_FORMAT(ClassDate, '%W') AS 'WeekDay' FROM Timetable) AS WeekDayTable
                    WHERE WEEKOFYEAR(ClassDate)=%s;
                """,(WeekNum,))
    dbresultDate=cur.fetchone()
    cur=getCursor() 
    cur.execute("""
                                        
            SELECT TimeTable.StartTime, Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday
            FROM
            (SELECT DISTINCT StartTime FROM LincolnGym.Timetable) AS TimeTable
            LEFT JOIN
            (SELECT
            t.StartTime,
            MAX(CASE WHEN WeekDayTable.WeekDay = 'Monday' THEN CONCAT(t.ClassID,',',c.ClassName,',',concat(tr.Firstname,' ',tr.LastName),',',t.ClassCode,',',c.Capacity-ifnull(RemainTable.TotalBooked,0),',',c.Capacity) ELSE NULL END) AS Monday,
            MAX(CASE WHEN WeekDayTable.WeekDay = 'Tuesday' THEN CONCAT(t.ClassID,',',c.ClassName,',',concat(tr.Firstname,' ',tr.LastName),',',t.ClassCode,',',c.Capacity-ifnull(RemainTable.TotalBooked,0),',',c.Capacity) ELSE NULL END) AS Tuesday,
            MAX(CASE WHEN WeekDayTable.WeekDay = 'Wednesday' THEN CONCAT(t.ClassID,',',c.ClassName,',',concat(tr.Firstname,' ',tr.LastName),',',t.ClassCode,',',c.Capacity-ifnull(RemainTable.TotalBooked,0),',',c.Capacity) ELSE NULL END) AS Wednesday,
            MAX(CASE WHEN WeekDayTable.WeekDay = 'Thursday' THEN CONCAT(t.ClassID,',',c.ClassName,',',concat(tr.Firstname,' ',tr.LastName),',',t.ClassCode,',',c.Capacity-ifnull(RemainTable.TotalBooked,0),',',c.Capacity) ELSE NULL END) AS Thursday,
            MAX(CASE WHEN WeekDayTable.WeekDay = 'Friday' THEN CONCAT(t.ClassID,',',c.ClassName,',',concat(tr.Firstname,' ',tr.LastName),',',t.ClassCode,',',c.Capacity-ifnull(RemainTable.TotalBooked,0),',',c.Capacity) ELSE NULL END) AS Friday,
            MAX(CASE WHEN WeekDayTable.WeekDay = 'Saturday' THEN CONCAT(t.ClassID,',',c.ClassName,',',concat(tr.Firstname,' ',tr.LastName),',',t.ClassCode,',',c.Capacity-ifnull(RemainTable.TotalBooked,0),',',c.Capacity) ELSE NULL END) AS Saturday,
            MAX(CASE WHEN WeekDayTable.WeekDay = 'Sunday' THEN CONCAT(t.ClassID,',',c.ClassName,',',concat(tr.Firstname,' ',tr.LastName),',',t.ClassCode,',',c.Capacity-ifnull(RemainTable.TotalBooked,0),',',c.Capacity) ELSE NULL END) AS Sunday
            FROM Timetable t
            LEFT JOIN (SELECT ClassID,StartTime, DATE_FORMAT(ClassDate, '%W') AS 'WeekDay' FROM Timetable) AS WeekDayTable
            ON WeekDayTable.ClassID = t.ClassID
            LEFT JOIN (SELECT b.classID, COUNT(b.MemberID) AS"TotalBooked" FROM Booking b
            LEFT JOIN Timetable t
            ON b.ClassID = t.ClassID
            LEFT JOIN ClassType c
            ON c.ClassCode = t.ClassCode
            GROUP BY b.classID) AS RemainTable
            ON RemainTable.classID = t.ClassID
            LEFT JOIN Booking b
            ON b.ClassID = t.ClassID
            LEFT JOIN ClassType c
            ON c.ClassCode = t.ClassCode
            LEFT JOIN Trainer tr
            ON tr.TrainerID = t.TrainerID
            WHERE
            WEEKOFYEAR(t.ClassDate) Like %s 
            and c.ClassCode!=1
            GROUP BY t.StartTime) AS Table2
            ON TimeTable.StartTime = Table2.StartTime
            ORDER BY TimeTable.StartTime;
                                    """,(WeekNum,))
    #get data for database and process
    dbcols=[desc[0] for desc in cur.description]
    dbresult=cur.fetchall()
    print(type(dbresult[0][0]))
    for result in dbresult:
        print(result)

    listdb=[]
    listlayer=[]
    listclass=[]     
    for x in dbresult:  
        for y in x:
            if type(y)!=str or y=='':
                listlayer.append(y)
            else:
                for b in y.split(","):
                    listclass.append(b)    
                listlayer.append(listclass)
                listclass=[]
        listdb.append(listlayer)    
        listclass=[]
        listlayer=[]
    for list in listdb:
        print(list)    


    # listdb=[]
    # listlayer=[]
    # listclass=[]
    # listIndividualClassInfo=[]     
    # for x in dbresult:  
    #     for y in x:
    #         if type(y)!=str or y==None:
    #             listlayer.append(y)
    #         else:
    #             # if ; exists in the string,means there are two rows of class info in the same time
    #             if ';' in y:
    #                 for individualClassInfo in y.split(";"):
    #                     for eachElementOfIndividualClassInfo in individualClassInfo .split(","):
    #                         listIndividualClassInfo.append(eachElementOfIndividualClassInfo)    
    #                     listclass.append(listIndividualClassInfo)
    #                     listIndividualClassInfo=[]
    #                 listlayer.append(listclass)
    #                 listclass=[]      
    #             else:
    #                 for b in y.split(","):
    #                     listclass.append(b)    
    #                 listlayer.append(listclass)
    #                 listclass=[]        

    #     listdb.append(listlayer)    
    #     listclass=[]
    #     listlayer=[]

    # for x in listdb:
    #     print(x)

    return render_template("classes.html",
                            username=username,
                            dbcols=dbcols,
                            dbresult=listdb,
                            dateChosen=dateChosen,
                            dbresultDate=dbresultDate,
                            Today=Today,
                            maxdate=maxdate
                            )


@app.route("/classes/addClasses/process",methods=['POST'])
def addClasse():
    if "username" in session:
        username = session["username"]
        #Get MemberID
        cur = getCursor()
        cur.execute("SELECT * FROM Member where Member.Email=%s",(username,))
        dbresult1=cur.fetchall()
        memberStatus=dbresult1[0][-2]
        print(memberStatus)
        if memberStatus!='Inactive':
            MemberID=dbresult1[0][0]
            # the variable is to define where the data come from,and show different content to users or redirect to different pages
            WaitForProcess=request.form['WaitForProcess']
            # if BookedClassDetails==1 show button link back to my booking page
            BookedClassDetails=request.form['BookedClassDetails']

            
            #if WaitForProcess=='1',show members the detailed class info page first with the booking button.
            if WaitForProcess=='1':
                ptsessionbook=request.form['ptsessionbook']
                #GET classID
                ClassID=request.form['ClassID']
                print('ClassID',ClassID)
                print("1")
                cur = getCursor()
                cur.execute("""
                                select distinct t.ClassID,c.ClassName,concat(tr.Firstname,' ',tr.LastName) as 'Trainer Name',DATE_FORMAT(t.ClassDate,'%d-%b-%Y'),WeekDayTable.WeekDay,t.StartTime,t.EndTime,CONCAT(ClassDate, ' ', StartTime) AS 'DateTime',tr.TrainerID,
                                (c.Capacity-ifnull(RemainTable.TotalBooked,0)) as"TotalRemaining",c.Capacity,c.ClassDescription
                                from Timetable t
                                left join 
                                (select ClassID,date_format(ClassDate,'%W') as 'WeekDay' from Timetable) as WeekDayTable
                                on WeekDayTable.ClassID=t.ClassID
                                left join (select b.classID,count(b.MemberID) as"TotalBooked" from Booking b
                                left join Timetable t
                                on b.ClassID=t.ClassID
                                left join ClassType c
                                on c.ClassCode=t.ClassCode
                                group by b.classID) as RemainTable
                                on  RemainTable.classID=t.ClassID
                                left join Booking b
                                on b.ClassID=t.ClassID
                                left join ClassType c
                                on c.ClassCode=t.ClassCode
                                left join Trainer tr
                                on tr.TrainerID=t.TrainerID
                                where t.ClassID=%s
                                """,(ClassID,))
                dbresultClassInfo=cur.fetchall()
                #Validation
                #check if the class has been booked.If yes,disable the book button
                cur.execute("""select ClassID from Booking
                                where MemberID=%s""",(MemberID,))
                BookingValidationDB=cur.fetchall()
                BookingValidation=[]
                for x in BookingValidationDB:
                    for y in x:
                        y=str(y)
                        BookingValidation.append(y)
                now = datetime.now()
                # print(dbresultClassInfo[0][7])
                # print(type(dbresultClassInfo[0][7]))
                ClassDateTime=datetime.strptime(dbresultClassInfo[0][7], '%Y-%m-%d %H:%M:%S')
        
                # print(type(ClassDateTime))
                # print(ClassDateTime)
                if ClassDateTime<now:
                    DisableBookButton='Yes'
                else:
                    DisableBookButton='No'     
                
                # prevent members book past        
                
                return render_template("ClassBook.html",section="#DisplayFirst",
                            dbresultClassInfo=dbresultClassInfo,
                            ClassID=ClassID,
                            BookingValidation=BookingValidation,
                            username=username,
                            BookedClassDetails=BookedClassDetails,
                                DisableBookButton=DisableBookButton,
                                ptsessionbook=ptsessionbook)
            # WaitForProcess=='0' Means the member has pressed the book button.Get corresponding Class info and book the member in the class.
            elif WaitForProcess=='0':
                ClassID=request.form['ClassID']
                #get related class info for the new class need to be added.
                cur.execute("""
                            select t.ClassID,t.ClassDate,t.StartTime,c.ClassName from Timetable t
                            left join ClassType c
                            on c.Classcode=t.ClassCode
                            where t.ClassID=%s
                            """,(ClassID,))
                dbresultClassTobeBooked=cur.fetchall()
                ClassDateTobeBooked=dbresultClassTobeBooked[0][1]
                ClassTimeTobeBooked=dbresultClassTobeBooked[0][2]
                #validation for same time same date booking.Prevent double booking.
                cur.execute("""
                            select t.ClassID,c.ClassName,t.ClassDate,t.StartTime,t.EndTime,DATE_FORMAT(t.ClassDate,'%d-%b-%Y') from Booking b
                            left join Timetable t
                            on b.ClassID=t.ClassID
                            left join ClassType c
                            on c.ClassCode=t.ClassCode
                            left join Member m
                            on m.MemberID=b.MemberID
                            where b.MemberID=%s
                            and t.ClassDate=%s
                            and t.StartTime=%s
                            order by t.ClassDate;
                            """,(MemberID,ClassDateTobeBooked,ClassTimeTobeBooked))
                dbresultValidation=cur.fetchall()
                # print(dbresultValidation)
                # print(type(dbresultValidation))
                #if dbresult is empty means there is no classes booked in this specific datetime
                if dbresultValidation==[]:
                    #then book the new class in
                    cur.execute("insert into Booking (MemberID,ClassID,IsPaid,BookingStatus) values(%s,%s,'0','Current')",(MemberID,ClassID))
                    #After the course reservation is successful, redirect the user to the "My Reservations" page which displays 
                    # the latest reservation information.
                    sql = """select ClassDate from Timetable 
                            where ClassID=%s"""
                    cur.execute(sql, (ClassID,))
                    ClassDateDB = cur.fetchone()
                    # print('done')
                    ClassDate=ClassDateDB[0].strftime("%Y-%m-%d")
                    flash('The Class has been added to your list!',"successBooked")
                    return redirect(f"/myBooking?dateChosen={ClassDate}")
                else:
                    # flash(f"Fail to add {dbresultClassTobeBooked[0][-1]} to your list because you have already scheduled {dbresultValidation[0][1]} at {dbresultValidation[0][3]} on {dbresultValidation[0][-1]}.","errorbook")
                    flash(f'Fail to add {dbresultClassTobeBooked[0][-1]}! to your list.You have scheduled for another class at same time.',"errorbook")
                    return redirect(f"/myBooking")
                    
            else:
                #If fail adding class.Print error notice.
                # flash('Something wrong!',"error")
                return redirect(f"/classes")
        else:
            flash("Sorry! Only active members can book a class.")
            return redirect(url_for("home"))    
    else:
        flash("Please login to book a class!")
        return redirect(url_for("home"))
        



@app.route("/ptCalendar")
def ptCalendar():
    if "username" in session:
        username = session["username"]
    else:
        username=''
    #get user input date info
    dateChosen=request.args.get("dateChosen","")
    #if user input is empty,show current date class schedule
    #min date(today)
    Today=date.today()
    #max date
    three_weeks = timedelta(weeks=3)
    maxdate = Today + three_weeks
    if dateChosen=="" : 
        dateChosen=Today
        WeekNum=Today.strftime("%W")
    else:
        dateChosen=datetime.strptime(dateChosen, '%Y-%m-%d').date()
        WeekNum=int(dateChosen.strftime("%W"))
    WeekNum=f"{WeekNum}%"
    #get date
    cur=getCursor() 
    cur.execute("""SELECT DISTINCT 
                    'Date' AS StartTime,
                    DATE_FORMAT(MAX(CASE WHEN WeekDayTable.WeekDay = 'Monday' THEN WeekDayTable.ClassDate ELSE '' END), '%d-%b-%Y') AS Monday,
                    DATE_FORMAT(MAX(CASE WHEN WeekDayTable.WeekDay = 'Tuesday' THEN WeekDayTable.ClassDate ELSE '' END), '%d-%b-%Y') AS Tuesday,
                    DATE_FORMAT(MAX(CASE WHEN WeekDayTable.WeekDay = 'Wednesday' THEN WeekDayTable.ClassDate ELSE '' END), '%d-%b-%Y') AS Wednesday,
                    DATE_FORMAT(MAX(CASE WHEN WeekDayTable.WeekDay = 'Thursday' THEN WeekDayTable.ClassDate ELSE '' END), '%d-%b-%Y') AS Thursday,
                    DATE_FORMAT(MAX(CASE WHEN WeekDayTable.WeekDay = 'Friday' THEN WeekDayTable.ClassDate ELSE '' END), '%d-%b-%Y') AS Friday,
                    DATE_FORMAT(MAX(CASE WHEN WeekDayTable.WeekDay = 'Saturday' THEN WeekDayTable.ClassDate ELSE '' END), '%d-%b-%Y') AS Saturday,
                    DATE_FORMAT(MAX(CASE WHEN WeekDayTable.WeekDay = 'Sunday' THEN WeekDayTable.ClassDate ELSE '' END), '%d-%b-%Y') AS Sunday
                    FROM (SELECT ClassID,ClassDate, DATE_FORMAT(ClassDate, '%W') AS 'WeekDay' FROM Timetable) AS WeekDayTable
                    WHERE WEEKOFYEAR(ClassDate)=%s;
                """,(WeekNum,))
    dbresultDate=cur.fetchone()
    cur=getCursor() 
    cur.execute("""
                SELECT TimeTable.StartTime, Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday
                FROM
                (SELECT DISTINCT StartTime FROM LincolnGym.Timetable) AS TimeTable
                LEFT JOIN
                (SELECT
                t.StartTime,                                                
                GROUP_CONCAT(distinct CASE WHEN WeekDayTable.WeekDay = 'Monday' THEN CONCAT(t.ClassID,',',c.ClassName,',',concat(tr.Firstname,' ',tr.LastName),',',tr.trainerID,',',t.ClassDate,',',t.StartTime,',',t.EndTime,',',dayofweek(t.ClassDate),',',c.Capacity-ifnull(RemainTable.TotalBooked,0),',',c.Capacity) ELSE NULL END SEPARATOR ';') AS Monday,
                GROUP_CONCAT(distinct CASE WHEN WeekDayTable.WeekDay = 'Tuesday' THEN CONCAT(t.ClassID,',',c.ClassName,',',concat(tr.Firstname,' ',tr.LastName),',',tr.trainerID,',',t.ClassDate,',',t.StartTime,',',t.EndTime,',',dayofweek(t.ClassDate),',',c.Capacity-ifnull(RemainTable.TotalBooked,0),',',c.Capacity) ELSE NULL END SEPARATOR ';') AS Tuesday,
                GROUP_CONCAT(distinct CASE WHEN WeekDayTable.WeekDay = 'Wednesday' THEN CONCAT(t.ClassID,',',c.ClassName,',',concat(tr.Firstname,' ',tr.LastName),',',tr.trainerID,',',t.ClassDate,',',t.StartTime,',',t.EndTime,',',dayofweek(t.ClassDate),',',c.Capacity-ifnull(RemainTable.TotalBooked,0),',',c.Capacity) ELSE NULL END SEPARATOR ';') AS Wednesday,
                GROUP_CONCAT(distinct CASE WHEN WeekDayTable.WeekDay = 'Thursday' THEN CONCAT(t.ClassID,',',c.ClassName,',',concat(tr.Firstname,' ',tr.LastName),',',tr.trainerID,',',t.ClassDate,',',t.StartTime,',',t.EndTime,',',dayofweek(t.ClassDate),',',c.Capacity-ifnull(RemainTable.TotalBooked,0),',',c.Capacity) ELSE NULL END SEPARATOR ';') AS Thursday,
                GROUP_CONCAT(distinct CASE WHEN WeekDayTable.WeekDay = 'Friday' THEN CONCAT(t.ClassID,',',c.ClassName,',',concat(tr.Firstname,' ',tr.LastName),',',tr.trainerID,',',t.ClassDate,',',t.StartTime,',',t.EndTime,',',dayofweek(t.ClassDate),',',c.Capacity-ifnull(RemainTable.TotalBooked,0),',',c.Capacity) ELSE NULL END SEPARATOR ';') AS Friday,
                GROUP_CONCAT(distinct CASE WHEN WeekDayTable.WeekDay = 'Saturday' THEN CONCAT(t.ClassID,',',c.ClassName,',',concat(tr.Firstname,' ',tr.LastName),',',tr.trainerID,',',t.ClassDate,',',t.StartTime,',',t.EndTime,',',dayofweek(t.ClassDate),',',c.Capacity-ifnull(RemainTable.TotalBooked,0),',',c.Capacity) ELSE NULL END SEPARATOR ';') AS Saturday,
                GROUP_CONCAT(distinct CASE WHEN WeekDayTable.WeekDay = 'Sunday' THEN CONCAT(t.ClassID,',',c.ClassName,',',concat(tr.Firstname,' ',tr.LastName),',',tr.trainerID,',',t.ClassDate,',',t.StartTime,',',t.EndTime,',',dayofweek(t.ClassDate),',',c.Capacity-ifnull(RemainTable.TotalBooked,0),',',c.Capacity) ELSE NULL END SEPARATOR ';') AS Sunday
                FROM Timetable t
                LEFT JOIN (SELECT ClassID,StartTime, DATE_FORMAT(ClassDate, '%W') AS 'WeekDay' FROM Timetable) AS WeekDayTable
                ON WeekDayTable.ClassID = t.ClassID
                LEFT JOIN (SELECT b.classID, COUNT(b.MemberID) AS"TotalBooked" FROM Booking b
                LEFT JOIN Timetable t
                ON b.ClassID = t.ClassID
                LEFT JOIN ClassType c
                ON c.ClassCode = t.ClassCode
                GROUP BY b.classID) AS RemainTable
                ON RemainTable.classID = t.ClassID
                LEFT JOIN Booking b
                ON b.ClassID = t.ClassID
                LEFT JOIN ClassType c
                ON c.ClassCode = t.ClassCode
                LEFT JOIN Trainer tr
                ON tr.TrainerID = t.TrainerID
                WHERE WEEKOFYEAR(t.ClassDate) Like %s 
                and c.ClassCode=1
                GROUP BY t.StartTime) AS Table2
                ON TimeTable.StartTime = Table2.StartTime
                ORDER BY TimeTable.StartTime;
                                    """,(WeekNum,))
    #get data for database and process
    dbcols=[desc[0] for desc in cur.description]
    dbresult=cur.fetchall()
    # # print(type(dbresult[0][0]))
    # for result in dbresult:
    #     print(result)

    # listdb=[]
    # listlayer=[]
    # listclass=[]     
    # for x in dbresult:  
    #     for y in x:
    #         if type(y)!=str or y=='':
    #             listlayer.append(y)
    #         else:
    #             for b in y.split(","):
    #                 listclass.append(b)    
    #             listlayer.append(listclass)
    #             listclass=[]
    #     listdb.append(listlayer)    
    #     listclass=[]
    #     listlayer=[]


    listdb=[]
    listlayer=[]
    listclass=[]
    listIndividualClassInfo=[]     
    for x in dbresult:  
        for y in x:
            if type(y)!=str or y==None:
                listlayer.append(y)
            else:
                # if ; exists in the string,means there are two rows of class info in the same time
                if ';' in y:
                    for individualClassInfo in y.split(";"):
                        for eachElementOfIndividualClassInfo in individualClassInfo .split(","):
                            listIndividualClassInfo.append(eachElementOfIndividualClassInfo)    
                        listclass.append(listIndividualClassInfo)
                        listIndividualClassInfo=[]
                    listlayer.append(listclass)
                    listclass=[]      
                else:
                    for b in y.split(","):
                        listclass.append(b)    
                    listlayer.append(listclass)
                    listclass=[]        

        listdb.append(listlayer)    
        listclass=[]
        listlayer=[]

    for x in listdb:
        print(x)





    return render_template("PTcalendar.html",
                            username=username,
                            dbcols=dbcols,
                            dbresult=listdb,
                            dateChosen=dateChosen,
                            dbresultDate=dbresultDate,
                            Today=Today,
                            maxdate=maxdate)






@app.route("/ptsession")
def ptsession():
    if "username" in session:
        userID = session["userID"]
        cur=getCursor()
        cur.execute("SELECT * FROM role WHERE role='member'")
        memberIDList = []
        memberIDs = cur.fetchall()
        for memberID in memberIDs:
            memberIDList.append(memberID[0])
        if userID in memberIDList:
            cur = getCursor()
            username = session["username"]
            cur.execute("SELECT MemberStatus FROM member WHERE Email=%s",(username,))
            member_result = cur.fetchall()
            memberStatus = member_result[0][0]
            print(memberStatus)
            sql_trainer = "SELECT TrainerID, FirstName, LastName FROM trainer WHERE TrainerStatus='Active' ORDER BY FirstName "
            cur.execute(sql_trainer)
            trainerList = cur.fetchall()
        
            sql_timetable = """SELECT timetable.TrainerID, timetable.ClassDate, timetable.StartTime, timetable.EndTime, DAYOFWEEK(timetable.ClassDate), timetable.ClassID 
                            FROM timetable
                            WHERE  timetable.ClassCode = 1 AND DATE(timetable.ClassDate) > %s
                            ORDER BY timetable.ClassDate
                                                
            """
            cur.execute(sql_timetable,(datetime.today(),))
            timetableList = cur.fetchall()
            dayHelper = [1,2,3,4,5,6,7]
            weekDayList = [(1,'SUN'),(2,'MON'),(3,'TUE'),(4,'WED'),(5,'THU'),(6,'FRI'),(7,'SAT')]
            #sql_booking = """SELECT ClassID FROM booking WHERE IsPaid=1 AND BookingStatus='Current'"""
            #check if the session is already booked, if booked, disable button
            sql_existed_session = """SELECT timetable.ClassID, timetable.ClassCode, timetable.ClassDate FROM timetable
                                    INNER JOIN booking ON timetable.ClassID = booking.ClassID 
                                    WHERE IsPaid=1  AND timetable.ClassCode=1 AND DATE(timetable.ClassDate) > %s """
            cur.execute(sql_existed_session,(datetime.today(),))
            existedSessionData = cur.fetchall()
            # print(existedSessionData)
            existedSessionList = []
            for existedSession in existedSessionData:
                existedSessionList.append(existedSession[0])
            print(existedSessionList)
            return render_template("ptSession.html", username=username, trainerList=trainerList, timetableList=timetableList, weekDayList=weekDayList, dayHelper=dayHelper, existedSessionList=existedSessionList,memberStatus=memberStatus)
        else:
            session.pop("username", None)
            return redirect(url_for("ptsession"))
    else:
        cur = getCursor()
        sql_trainer = "SELECT TrainerID, FirstName, LastName FROM trainer WHERE TrainerStatus='Active' ORDER BY FirstName "
        
        cur.execute(sql_trainer)
        trainerList = cur.fetchall()
       
        sql_timetable = """SELECT timetable.TrainerID, timetable.ClassDate, timetable.StartTime, timetable.EndTime, DAYOFWEEK(timetable.ClassDate) 
                        FROM timetable
                        WHERE  timetable.ClassCode = 1 AND DATE(timetable.ClassDate) > %s
                        ORDER BY timetable.ClassDate
                                               
        """
        cur.execute(sql_timetable,(datetime.today(),))
        timetableList = cur.fetchall()
        dayHelper = [1,2,3,4,5,6,7]
        weekDayList = [(1,'SUN'),(2,'MON'),(3,'TUE'),(4,'WED'),(5,'THU'),(6,'FRI'),(7,'SAT')]
        return render_template("ptSession.html", trainerList=trainerList, timetableList=timetableList, weekDayList=weekDayList, dayHelper=dayHelper)
# book session function
@app.route("/bookSession",methods=["POST"])
def bookSession():
    username = session["username"]
    cur = getCursor()
    cur.execute("SELECT * FROM Member where Member.Email=%s",(username,))
    member = cur.fetchone()
    memberID = member[0]
    classID=request.form['classID']
    bankaccount= request.form['bankaccount']
    expireMonth = request.form['expireMonth']
    expireYear = request.form['expireYear']
    bankcvc= request.form['bankcvc']
    currentMonth = datetime.now().month
    currentYear = datetime.now().year
    isCardValid = False
    if (int(expireYear) == currentYear and int(expireMonth) >= currentMonth) or int(expireYear) > currentYear:
        isCardValid = True
    if len(bankaccount)==16  and len(bankcvc)>2 and isCardValid :
        
        cur = getCursor()
        sql_addBooking = """INSERT INTO booking(MemberID,ClassID,IsPaid,BookingStatus)
                            VALUES(%s,%s,%s,%s) """
        cur.execute(sql_addBooking,(memberID,classID,1,"Current"))
        # flash("You have booked a PT session successfully!")
        flash('PT session has been added to your list!',"successBooked")
        return redirect(url_for("myBooking"))
    else: 
        flash("payment is fail,try again")
        return redirect(url_for("ptsession"))
        

@app.route("/membership")
def membership():
    if "username" in session:
        username = session["username"]
        return render_template("membership.html", username=username)
    else:
        return render_template("membership.html")
#My profile section
@app.route("/myProfile")
def myProfile():
    if "username" in session:
        username = session["username"]     
        cur = getCursor()
        cur.execute("SELECT * FROM Member where Member.Email=%s",(username,))
        select_result = cur.fetchone()
        print(select_result)
        return render_template("myProfile.html", username=username, select_result=select_result)
    else:
        return redirect(url_for("home"))
    
@app.route("/myProfile/edit")
def myProfileEditGet():
    if "username" in session:
        username = session["username"]
        cur = getCursor()
        cur.execute("SELECT * FROM Member where Member.Email=%s",(username,))
        select_result = cur.fetchone()
        print(select_result)
        return render_template("myProfileEdit.html", username=username, select_result=select_result)
    else:
        return redirect(url_for("home"))

#My profile edit section
@app.route("/myProfileEditPOST",methods=["POST"])   
def myProfileEdit():
    if "username" in session:
        username = session["username"]
        memberID=request.form['memberID']
        firstname=request.form['firstname']
        lastname=request.form['lastname']
        email=request.form['email']
        phone=request.form['phone']
        PhysicalAddress=request.form['physicaladdress']
        DOB=request.form['birthdate']
        EmergencyName=request.form['emergencycontactname']
        EmergencyNumber=request.form['emergencycontactnumber']
        Mconditions=request.form['medicalconditions']
        # gymjoindate=request.form['gymjoindate']
        ReceivingNotifications=request.form['receivingnotifications']
        autoFee=request.form['authorityoncollectingfees']
        BankName=request.form['bankname']
        BankAccountHolderName=request.form['bankaccountholdername']
        BankAccountNumber=request.form['bankaccountnumber']
        MemberNotes=request.form['notes']
        cur=getCursor()
        sql="""update Member set FirstName=%s, LastName=%s,Email=%s, PhysicalAddress=%s, Phone=%s, DateOfBirth=%s,
                EmergencyContactName=%s, EmergencyContactNumber=%s, MedicalConditions=%s, ReceivingNotifications=%s,
                AuthorityOnCollectingFees=%s, BankName=%s, BankAccountHolderName=%s, BankAccountNumber=%s ,MemberNotes=%s
                where memberID=%s"""
        cur.execute(sql,(firstname,lastname,email,PhysicalAddress,phone,DOB,EmergencyName,EmergencyNumber,Mconditions,ReceivingNotifications,autoFee,BankName,BankAccountHolderName,BankAccountNumber,MemberNotes,memberID))
        #render the the same member page with same memberID
        cur.execute("select * from Member where MemberID=%s",(memberID,))
        select_result = cur.fetchone()
        flash("Details have been successfully updated")
        return redirect(url_for("myProfile"))
    else:
        return redirect(url_for("home"))



#My Booking section
@app.route("/myBooking")
def myBooking():
    if "username" in session:
        username = session["username"]
        #get MemberID
        cur = getCursor()
        cur.execute("SELECT * FROM Member where Member.Email=%s",(username,))
        dbresult1=cur.fetchall()
        MemberID=dbresult1[0][0]
        dateChosen=request.args.get("dateChosen","")
         #if user input is empty,show current date class booking record
        if dateChosen=="" :
            Today=date.today()
            dateChosen=Today
            WeekNum=Today.strftime("%W")
        else:
            dateChosen=datetime.strptime(dateChosen, '%Y-%m-%d').date()
            WeekNum=int(dateChosen.strftime("%W"))
        WeekNum=f"{WeekNum}%"
        #get date for each weeknum
        cur=getCursor() 
        cur.execute("""SELECT DISTINCT 
                        'Date' AS StartTime,
                        DATE_FORMAT(MAX(CASE WHEN WeekDayTable.WeekDay = 'Monday' THEN WeekDayTable.ClassDate ELSE '' END), '%d-%b-%Y') AS Monday,
                        DATE_FORMAT(MAX(CASE WHEN WeekDayTable.WeekDay = 'Tuesday' THEN WeekDayTable.ClassDate ELSE '' END), '%d-%b-%Y') AS Tuesday,
                        DATE_FORMAT(MAX(CASE WHEN WeekDayTable.WeekDay = 'Wednesday' THEN WeekDayTable.ClassDate ELSE '' END), '%d-%b-%Y') AS Wednesday,
                        DATE_FORMAT(MAX(CASE WHEN WeekDayTable.WeekDay = 'Thursday' THEN WeekDayTable.ClassDate ELSE '' END), '%d-%b-%Y') AS Thursday,
                        DATE_FORMAT(MAX(CASE WHEN WeekDayTable.WeekDay = 'Friday' THEN WeekDayTable.ClassDate ELSE '' END), '%d-%b-%Y') AS Friday,
                        DATE_FORMAT(MAX(CASE WHEN WeekDayTable.WeekDay = 'Saturday' THEN WeekDayTable.ClassDate ELSE '' END), '%d-%b-%Y') AS Saturday,
                        DATE_FORMAT(MAX(CASE WHEN WeekDayTable.WeekDay = 'Sunday' THEN WeekDayTable.ClassDate ELSE '' END), '%d-%b-%Y') AS Sunday
                        FROM (SELECT ClassID,ClassDate, DATE_FORMAT(ClassDate, '%W') AS 'WeekDay' FROM Timetable) AS WeekDayTable
                        WHERE WEEKOFYEAR(ClassDate)=%s;
                    """,(WeekNum,))
        dbresultDate=cur.fetchone()
        #get my booking details
        cur=getCursor()
        #get related 'current' class booking info for each member,Cancelled class will not show on table.
        cur.execute("""   
                SELECT TimeTable.StartTime, Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday
                FROM
                (SELECT DISTINCT StartTime FROM LincolnGym.Timetable) AS TimeTable
                LEFT JOIN
                (SELECT
                t.StartTime,
                MAX(CASE WHEN WeekDayTable.WeekDay = 'Monday' THEN CONCAT(t.ClassID,',',c.ClassName,',',concat(tr.Firstname,' ',tr.LastName),',',DATE_FORMAT(t.ClassDate,'%d-%b-%Y'),',',t.StartTime,',',t.EndTime,',',t.ClassCode) ELSE NULL END) AS Monday,
                MAX(CASE WHEN WeekDayTable.WeekDay = 'Tuesday' THEN CONCAT(t.ClassID,',',c.ClassName,',',concat(tr.Firstname,' ',tr.LastName),',',DATE_FORMAT(t.ClassDate,'%d-%b-%Y'),',',t.StartTime,',',t.EndTime,',',t.ClassCode) ELSE NULL END) AS Tuesday,
                MAX(CASE WHEN WeekDayTable.WeekDay = 'Wednesday' THEN CONCAT(t.ClassID,',',c.ClassName,',',concat(tr.Firstname,' ',tr.LastName),DATE_FORMAT(t.ClassDate,'%d-%b-%Y'),',',t.StartTime,',',t.EndTime,',',t.ClassCode) ELSE NULL END) AS Wednesday,
                MAX(CASE WHEN WeekDayTable.WeekDay = 'Thursday' THEN CONCAT(t.ClassID,',',c.ClassName,',',concat(tr.Firstname,' ',tr.LastName),',',DATE_FORMAT(t.ClassDate,'%d-%b-%Y'),',',t.StartTime,',',t.EndTime,',',t.ClassCode) ELSE NULL END) AS Thursday,
                MAX(CASE WHEN WeekDayTable.WeekDay = 'Friday' THEN CONCAT(t.ClassID,',',c.ClassName,',',concat(tr.Firstname,' ',tr.LastName),',',DATE_FORMAT(t.ClassDate,'%d-%b-%Y'),',',t.StartTime,',',t.EndTime,',',t.ClassCode) ELSE NULL END) AS Friday,
                MAX(CASE WHEN WeekDayTable.WeekDay = 'Saturday' THEN CONCAT(t.ClassID,',',c.ClassName,',',concat(tr.Firstname,' ',tr.LastName),',',DATE_FORMAT(t.ClassDate,'%d-%b-%Y'),',',t.StartTime,',',t.EndTime,',',t.ClassCode) ELSE NULL END) AS Saturday,
                MAX(CASE WHEN WeekDayTable.WeekDay = 'Sunday' THEN CONCAT(t.ClassID,',',c.ClassName,',',concat(tr.Firstname,' ',tr.LastName),',',DATE_FORMAT(t.ClassDate,'%d-%b-%Y'),',',t.StartTime,',',t.EndTime,',',t.ClassCode) ELSE NULL END) AS Sunday
                FROM Timetable t
                LEFT JOIN (SELECT ClassID,StartTime, DATE_FORMAT(ClassDate, '%W') AS 'WeekDay' FROM Timetable) AS WeekDayTable
                ON WeekDayTable.ClassID = t.ClassID
                LEFT JOIN (SELECT b.classID, COUNT(b.MemberID) AS"TotalBooked" FROM Booking b
                LEFT JOIN Timetable t
                ON b.ClassID = t.ClassID
                LEFT JOIN ClassType c
                ON c.ClassCode = t.ClassCode
                GROUP BY b.classID) AS RemainTable
                ON RemainTable.classID = t.ClassID
                LEFT JOIN Booking b
                ON b.ClassID = t.ClassID
                LEFT JOIN ClassType c
                ON c.ClassCode = t.ClassCode
                LEFT JOIN Trainer tr
                ON tr.TrainerID = t.TrainerID
                WHERE
                b.MemberID=%s AND
                b.BookingStatus='Current' and
                WEEKOFYEAR(t.ClassDate) Like %s 
                GROUP BY t.StartTime) AS Table2
                ON TimeTable.StartTime = Table2.StartTime
                ORDER BY TimeTable.StartTime;""",(MemberID,WeekNum))
        dbcols=[desc[0] for desc in cur.description]
        dbresult=cur.fetchall()
        #get data for database and process
        listdb=[]
        listlayer=[]
        listclass=[]     
        for x in dbresult:  
            for y in x:
                if type(y)!=str or y=='':
                    listlayer.append(y)
                else:
                    for b in y.split(","):
                        listclass.append(b)    
                    listlayer.append(listclass)
                    listclass=[]
            listdb.append(listlayer)    
            listclass=[]
            listlayer=[]
        return render_template("myBooking.html",
                        username=username,
                        dbcols=dbcols,
                        dbresult=listdb,
                        dateChosen=dateChosen,
                        dbresultDate=dbresultDate,
                        MemberID=MemberID)    

        # cur = getCursor()
        # cur.execute("SELECT * FROM Member where Member.Email=%s",(username,))
        # member = cur.fetchone()
        # memberID = member[0]
        # sql_session_booking = """SELECT booking.MemberID,CONCAT(trainer.FirstName," ", trainer.LastName) AS TrainerName,  timetable.ClassDate, timetable.StartTime, timetable.EndTime, DAYOFWEEK(timetable.ClassDate),timetable.ClassID FROM timetable
        #                         INNER JOIN booking ON booking.ClassID = timetable.ClassID
        #                         INNER JOIN trainer ON timetable.TrainerID = trainer.TrainerID
        #                         WHERE timetable.ClassCode=1 AND booking.BookingStatus='Current' AND booking.MemberID = %s AND DATE(timetable.ClassDate) > %s
        #                         ORDER BY timetable.ClassDate """
        # cur.execute(sql_session_booking, (memberID, datetime.today()))
        # myBookingList = cur.fetchall()
        # cancelAvailableDay = date.today() + timedelta(days=7)
        # # print(cancelAvailableDay)
        # dayHelper = [1,2,3,4,5,6,7]
        # weekDayList = [(1,'SUN'),(2,'MON'),(3,'TUE'),(4,'WED'),(5,'THU'),(6,'FRI'),(7,'SAT')]
        # print(len(myBookingList))
        # return render_template("myBooking.html", username=username,
        #                                         dayHelper=dayHelper,
        #                                         weekDayList=weekDayList,
        #                                         myBookingList=myBookingList,
        #                                         cancelAvailableDay=cancelAvailableDay
        #                        )
    else:
        return redirect(url_for("home"))

#cancel class
@app.route("/cancelClass", methods=["POST"])
def cancelClass():
    ClassID = request.form["ClassID"]
    MemberID = request.form["MemberID"]
    #if classDate is less than a week before today. No refund
    cur=getCursor()
    sql = """   select t.ClassDate,CONCAT(ClassDate, ' ', StartTime) AS 'DateTime',c.ClassCode,c.ClassName from Timetable t
                left join ClassType c
                on c.Classcode=t.ClassCode
                where t.ClassID=%s"""
    cur.execute(sql, (ClassID,))
    ClassDateDB = cur.fetchone()
    ClassCode=ClassDateDB[-2]
    ClassDate=ClassDateDB[0].strftime("%Y-%m-%d")
    ClassDateTime=datetime.strptime(ClassDateDB[1], '%Y-%m-%d %H:%M:%S')
    now = datetime.now()
    time_delta = ClassDateTime - now
    # if time_delta.days <0 MEANS it's in the past.
    if time_delta.days < 0:
        flash(f'Sorry!{ClassDateDB[-1]} scheduled for {ClassDateDB[0]} cannot be cancelled as the course has already taken place!',"error")
        return redirect(f"/myBooking?dateChosen={ClassDate}")

    else:
        # if > 7days,both pt session and class can get refund and places released for re-book
        # if < 7 days,only places for classes will be released for re-book
        if time_delta.days >7 or (time_delta.days <=7 and ClassCode!=1):
            cur=getCursor()
            sql = """DELETE FROM booking 
                    WHERE MemberID = %s AND ClassID = %s """       
            cur.execute(sql, (MemberID,ClassID))
            flash('The class has been cancelled successfully!',"successCancelled")
            return redirect("/myBooking")
        else:
            # pt sessions that are cancelled within 7 days members will not get the refund and 
            # the place for pt session will not be released.(cant re-book by other members)
            cur=getCursor()
            sql = """update booking set BookingStatus='Cancelled'
                    where ClassID=%s and MemberID=%s"""       
            cur.execute(sql, (ClassID,MemberID))
            flash('The class has been cancelled successfully!',"successCancelled")
            return redirect("/myBooking")

# # Cancel PT Session function
# @app.route("/cancelSession", methods=["POST"])
# def cancelSession():
#     classID = request.form.get("classID")
#     memberID = request.form.get("memberID")
#     cur=getCursor()
#     sql = """DELETE FROM booking WHERE MemberID = %s AND ClassID = %s """
#     cur.execute(sql, (memberID,classID))
#     return redirect(url_for("myBooking"))
# # Cancel PT Session no refund function
# @app.route("/cancelSessionNoRefund", methods=["POST"])
# def cancelSessionNoRefund():
#     classID = request.form.get("classID")
#     memberID = request.form.get("memberID")
#     cur=getCursor()
#     sql = """UPDATE booking SET BookingStatus='Cancelled'
#     WHERE MemberID = %s AND ClassID = %s """
#     cur.execute(sql, (memberID,classID))
#     return redirect(url_for("myBooking"))

@app.route("/myMessage")
def myMessage():
    if "username" in session:
        username = session["username"]
        cur = getCursor()
        cur.execute("SELECT * FROM Member where Member.Email=%s limit 2000 ",(username,))
        member = cur.fetchone()
        memberID = member[0]
        memberIsReceivingNotifation = member[11]
        memberStatus = member[17]
        memberJoinDate = member[10]
        current_time = datetime.now()
        today_date = datetime.now().day
        memberJoinDay = memberJoinDate.strftime('%d')
        today_date_int = int(today_date)
        memberJoinDay_int = int(memberJoinDay)
        sql_weeklyupdate = """SELECT * FROM weeklyupdate ORDER BY updateTime DESC LIMIT 1 """
        cur.execute(sql_weeklyupdate)
        weeklyupdate = cur.fetchall()
        sql_notice = """SELECT NoticeSubject, Content, NoticeDate FROM notice
                        WHERE MemberID=%s
                        ORDER BY NoticeDate DESC
                        LIMIT 60 """
        cur.execute(sql_notice,(memberID,))
        messageList = cur.fetchall()
        return render_template("myMessage.html", username=username, messageList=messageList,memberIsReceivingNotifation=memberIsReceivingNotifation,weeklyupdate=weeklyupdate,memberStatus=memberStatus,current_time=current_time,today_date_int=today_date_int,memberJoinDay_int=memberJoinDay_int)
    else:
        return redirect(url_for("home"))
    
# public interface login function
@app.route("/login", methods=["POST"])
def login_post():
    email = request.form.get("email")
    password = request.form.get("password")
    error = ""
    cur=getCursor()
    sql = """SELECT * FROM member WHERE Email = %s AND MemberPassword = %s """
    cur.execute(sql, (email,password))
    member = cur.fetchall()
    if len(member) == 1:
        if member[0][17]=="Archived":
            flash("You are an archived user, please contact gym staff for more information!")
            return render_template("base.html")   
        else:
            memberID = member[0][0]
            session["userID"] = memberID
            session["username"] = email
            return redirect(url_for("home"))
    else:
        flash("Invalid user name or password!")
        return render_template("base.html", error=error)   
# public interface logout function
@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("home"))

# public interface password reset function
@app.route("/resetPassword", methods=["POST"])
def password_reset():
    password = request.form.get("password")
    confirmPassword = request.form.get("confirmPassword")
    email = session["username"]
    error = ""
    cur=getCursor()
    # new password has to be at leat 8 characters
    if len(password)>7 and (password==confirmPassword):
        sql = """UPDATE member SET MemberPassword = %s WHERE Email = %s """
        cur.execute(sql, (password, email))
        flash("Password reset succeed!Please login with new password!")
        session.pop("username", None)
        return redirect(url_for("home"))
    else:
        error="***Error! Please reset again!***"
        return render_template("base.html", error=error)   
# admin login function
@app.route("/admin")
def adminLogin_get():
    return render_template("adminLogin.html")


@app.route("/admin/login", methods=["POST"])
def adminLogin_post():
    username = request.form.get("username")
    password = request.form.get("password")
    error = ""
    cur=getCursor()
    sql = """SELECT * FROM admin WHERE Username = %s AND UserPassword = %s """
    cur.execute(sql, (username,password))
    user = cur.fetchall()
    if len(user) == 1:
        userID = user[0][0]
        session["userID"] = userID
        session["username"] = username
        print("session(username):")
        return redirect(url_for("admin"))
    else:
        flash("Invalid user name or password!")
        return render_template("adminLogin.html")
    
@app.route("/admin/logout")
def adminLogout():
    session.pop("username", None)
    return redirect(url_for("adminLogin_get"))

# admin system
@app.route("/admin/dashboard")
def admin():
    if "username" in session:
        username = session["username"]
        return render_template("adminDashboard.html"
                               ,username=username
                               )
    else:
        return redirect(url_for("adminLogin_get"))

#Render Member List Page    
@app.route("/admin/member")
def MemberList():
    if "username" in session:
        username = session["username"]
        showMemberType=request.args.get("showMemberType","")
        showMemberType=f"{showMemberType}%"
        cur=getCursor()
        cur.execute("""Select MemberID,CONCAT(Firstname," ",Lastname) as 'Name',DateOfBirth,GymJoinDate,MemberStatus from Member
                        where  MemberStatus LIKE %s
                        order by CONCAT(Firstname," ",Lastname)""",(showMemberType,))
        dbcols=[desc[0] for desc in cur.description]
        dbresult=cur.fetchall()
        message_nodata="Sorry!No member information under this category!"
        return render_template("manageMember.html",
                            dbcols=dbcols,
                            dbresult=dbresult
                                ,username=username,
                                showMemberType=showMemberType,
                                message_nodata=message_nodata
                                )
    else:
        return redirect(url_for("adminLogin_get"))


# Render Trainer Workload for admin
@app.route("/admin/trainerwork", methods=['GET'])
def trainerwork():
    if "username" in session:
        sql_trainerwork = """Select t2.TrainerID, t2.TrainerName, count(t2.ClassDate) from (
                Select * from (
                Select tr.TrainerID, concat(FirstName, ' ', tr.LastName) as 'TrainerName', ct.ClassName, tb.ClassDate, tb.StartTime, tb.EndTime
                from Timetable tb
                left join ClassType ct on tb.ClassCode = ct.ClassCode
                left join Trainer tr on tb.TrainerID = tr.TrainerID
                Where tb.ClassCode != 1 and tb.ClassDate >= '2023-01-01' and tb.ClassDate <= '2023-12-31' 
                ) t ) t2
                group by t2.TrainerID, t2.TrainerName order by t2.TrainerID asc;"""
        username = session["username"]
        cur = getCursor()
        cur.execute(sql_trainerwork)
        dbcols = [desc[0] for desc in cur.description]
        dbresult = cur.fetchall()

        return render_template("managerTrainerWork.html",
                                username=username,
                                dbcols=dbcols,
                                dbresult=dbresult
                                )
    else:
        return redirect(url_for("adminLogin_get"))

# render trainer class work by selected date
@app.route("/admin/checkclasscount", methods=['POST'])
def checkclasscount():
    if "username" in session:
        trainer_class_count = """Select t2.TrainerID, t2.TrainerName, count(t2.ClassDate) from (
                            Select * from (
                            Select tr.TrainerID, concat(FirstName, ' ', tr.LastName) as 'TrainerName', ct.ClassName, tb.ClassDate, tb.StartTime, tb.EndTime
                            from Timetable tb
                            left join ClassType ct on tb.ClassCode = ct.ClassCode
                            left join Trainer tr on tb.TrainerID = tr.TrainerID
                            Where tb.ClassCode != 1 and tb.ClassDate >= %s and tb.ClassDate <= %s
                            ) t ) t2
                            group by t2.TrainerID, t2.TrainerName Order by t2.TrainerID;"""
        username = session["username"]

        startdate = request.form.get("startdate")
        enddate = request.form.get("enddate")
        cur = getCursor()
        cur.execute(trainer_class_count, (startdate, enddate,))
        dbcols = [desc[0] for desc in cur.description]
        dbresult = cur.fetchall()
        print(startdate)
        print(enddate)
        return render_template("manageTrainerWorkCount.html",
                                username=username,
                                startdate=startdate,
                                enddate=enddate,
                                dbcols=dbcols,
                                dbresult=dbresult
                                )


#Individual trainer class details
@app.route("/admin/trainer/workdetails",methods=["POST"])
def trainerclassdetails():
    if "username" in session:
        username = session["username"]
        trainerID=request.form["trainerID"]
        startdate = request.args.get('startdate')
        enddate = request.args.get('enddate')
        trainer_class_details = """Select concat(FirstName, ' ', tr.LastName) as 'TrainerName', 
                                    ct.ClassName, DATE_FORMAT(tb.ClassDate,'%d/%m/%Y'), tb.StartTime, tb.EndTime
                                    from Timetable tb
                                    left join ClassType ct on tb.ClassCode = ct.ClassCode
                                    left join Trainer tr on tb.TrainerID = tr.TrainerID
                                    Where tb.ClassCode != 1 and tb.ClassDate >= %s and tb.ClassDate <= %s and tb.TrainerID=%s
                                    Order by tb.ClassDate asc"""
        print(trainerID)
        print(startdate)
        print(enddate)
        cur=getCursor()
        cur.execute(trainer_class_details, (startdate, enddate, trainerID))
        dbcols=[desc[0] for desc in cur.description]
        dbresult=cur.fetchall()
        return render_template("manageTrainerDetailsSelectedDate.html",
                                username=username,
                                dbcols=dbcols,
                                 dbresult= dbresult,
                                 trainerID=trainerID
                                )
    else:
        return redirect(url_for("adminLogin_get"))

# Render the popularity report
@app.route("/admin/popularityreport", methods=['GET'])
def popularityreport():
    if "username" in session:
        popularity_sql = """Select px.ClassName, px.Trainer_Name, sum(px.Attended_Number) as 'Attended_Number', concat(convert(round(avg(px.Attdence_Rate), 2), char), '%') as 'Attdence_Rate'
from (
Select  tx.ClassName, tx.Trainer_Name, tx.Attended_Number, 
                concat(round(Convert((tx.Attended_Number/30)*100, char), 2),  '%') as 'Attdence_Rate' from (
                Select t.ClassDate, t.ClassName, t.Trainer_Name, count(t.MemberID) as 'Attended_Number' from (
                Select bk.MemberID, bk.ClassID, tt.ClassDate, ct.ClassName, concat(tr.FirstName, ' ', tr.LastName) as 'Trainer_Name',
                    tt.ClassCode
                from Booking bk
                left join Timetable tt on bk.ClassID = tt.ClassID
                left join ClassType ct on tt.ClassCode = ct.ClassCode
                left join Trainer tr on tt.TrainerID = tr.TrainerID
                Where ct.ClassCode != 1 and tt.ClassDate >= '2023-01-01' and  tt.ClassDate <= '2023-12-31') t 
                Group by t.ClassDate, t.ClassName, t.Trainer_Name) tx
                Where Attended_Number <= 30
                Order by Attended_Number desc) px
group by px.ClassName, px.Trainer_Name 
Order by avg(px.Attdence_Rate) desc;"""
        username = session["username"]
        cur = getCursor()
        cur.execute(popularity_sql)
        dbcols = [desc[0] for desc in cur.description]
        dbresult = cur.fetchall()

        return render_template("managerPopularityView.html",
                                username=username,
                                dbcols=dbcols,
                                dbresult=dbresult
                                )
    else:
        return redirect(url_for("adminLogin_get"))

# Select the specific date to view popularity
@app.route("/admin/checkpopbydate", methods=['POST'])
def checkpopbydate():
    if "username" in session:
        popularity_selected = """Select px.ClassName, px.Trainer_Name, sum(px.Attended_Number) as 'Attended_Number', concat(convert(round(avg(px.Attdence_Rate), 2), char), '%') as 'Attdence_Rate'
from (
Select  tx.ClassName, tx.Trainer_Name, tx.Attended_Number, 
                concat(round(Convert((tx.Attended_Number/30)*100, char), 2),  '%') as 'Attdence_Rate' from (
                Select t.ClassDate, t.ClassName, t.Trainer_Name, count(t.MemberID) as 'Attended_Number' from (
                Select bk.MemberID, bk.ClassID, tt.ClassDate, ct.ClassName, concat(tr.FirstName, ' ', tr.LastName) as 'Trainer_Name',
                    tt.ClassCode
                from Booking bk
                left join Timetable tt on bk.ClassID = tt.ClassID
                left join ClassType ct on tt.ClassCode = ct.ClassCode
                left join Trainer tr on tt.TrainerID = tr.TrainerID
                Where ct.ClassCode != 1 and tt.ClassDate >= %s and  tt.ClassDate <= %s) t 
                Group by t.ClassDate, t.ClassName, t.Trainer_Name) tx
                Where Attended_Number <= 30
                Order by Attended_Number desc) px
group by px.ClassName, px.Trainer_Name 
Order by avg(px.Attdence_Rate) desc;"""
        username = session["username"]

        startdate = request.form.get("startdate")
        enddate = request.form.get("enddate")
        cur = getCursor()
        cur.execute(popularity_selected, (startdate, enddate,))
        dbcols = [desc[0] for desc in cur.description]
        dbresult = cur.fetchall()
        print(startdate)
        print(enddate)
        return render_template("manageCheckPopularitybyDate.html",
                                username=username,
                                startdate=startdate,
                                enddate=enddate,
                                dbcols=dbcols,
                                dbresult=dbresult
                                )


# Generate Financial Report - summary
@app.route("/admin/financialreport", methods=['GET'])
def financialreport():
    if "username" in session:
        financial_sql = """Select ClassName, sum(Class_Fee) as 'Revenue' from (
                    Select sc.SubscriptionID, 'Member Subscription' as 'ClassName',  'Member Subscription' as 'Trainer_Name', sc.SubscriptionStartDate as 'Start_Date', 
                    sc.SubscriptionEndDate as 'End_Date', sc.PaymentAmount as 'Class_Fee'
                    from Subscription sc
                    left join Member m on sc.MemberID = m.MemberID
                    Union
                    -- PT training financial
                    Select tt.ClassID, ct.ClassName, concat(tr.FirstName, ' ', tr.LastName) as 'Trainer_Name', 
                    tt.ClassDate as 'Start_Date', tt.ClassDate as 'End_Date', 50 as 'Class_Fee'
                    from Timetable tt
                    left join ClassType ct on tt.ClassCode = ct.ClassCode
                    left join Trainer tr on tt.TrainerID = tr.TrainerID
                    Where tt.ClassCode = 1) t
                    Where t.Start_Date >= '2023-02-01' and t.End_Date <= '2023-12-01'
                    Group by ClassName;"""

        total_sql = """Select sum(Class_Fee) as 'Revenue' from (
                    Select sc.SubscriptionID, 'Member Subscription' as 'ClassName',  'Member Subscription' as 'Trainer_Name', sc.SubscriptionStartDate as 'Start_Date', 
                    sc.SubscriptionEndDate as 'End_Date', sc.PaymentAmount as 'Class_Fee'
                    from Subscription sc
                    left join Member m on sc.MemberID = m.MemberID
                    Union
                    -- PT training financial
                    Select tt.ClassID, ct.ClassName, concat(tr.FirstName, ' ', tr.LastName) as 'Trainer_Name', 
                    tt.ClassDate as 'Start_Date', tt.ClassDate as 'End_Date', 50 as 'Class_Fee'
                    from Timetable tt
                    left join ClassType ct on tt.ClassCode = ct.ClassCode
                    left join Trainer tr on tt.TrainerID = tr.TrainerID
                    Where tt.ClassCode = 1) t
                    Where t.Start_Date >= '2023-01-01' and t.End_Date <= '2023-12-01'"""

        single_pt_sql = """Select t3.Trainer_Name, sum(Class_Fee) from (
            Select tt.ClassID, ct.ClassName, concat(tr.FirstName, ' ', tr.LastName) as 'Trainer_Name', 
            tt.ClassDate as 'Start_Date', tt.ClassDate as 'End_Date', 50 as 'Class_Fee'
            from Timetable tt
            left join ClassType ct on tt.ClassCode = ct.ClassCode
            left join Trainer tr on tt.TrainerID = tr.TrainerID
            Where tt.ClassCode = 1) t3
            Where t3.Start_Date >= '2023-02-01' and t3.End_Date <= '2023-03-31'
            group by Trainer_Name"""

        username = session["username"]
        cur = getCursor()
        cur.execute(financial_sql)
        dbcols = [desc[0] for desc in cur.description]
        dbresult = cur.fetchall()

        cur_f = getCursor()
        cur_f.execute(total_sql)
        dbcols_f = [desc[0] for desc in cur_f.description]
        dbresult_f = cur_f.fetchall()

        cur_single = getCursor()
        cur_single.execute(single_pt_sql)
        dbcols_single = [desc[0] for desc in cur_single.description]
        dbresult_single = cur_single.fetchall()

        return render_template("managerFinancialReport.html",
                                username=username,
                                dbcols=dbcols,
                                dbresult=dbresult,
                               dbcols_f=dbcols_f,
                               dbresult_f=dbresult_f,
                               dbresult_single=dbresult_single,
                               dbcols_single=dbcols_single

                                )
    else:
        return redirect(url_for("adminLogin_get"))

# Select the specific date to filter financial report
@app.route("/admin/checkfinancebydate", methods=['POST'])
def checkfinancebydate():
    if "username" in session:
        if "username" in session:
            financial_sql_selected = """Select ClassName, sum(Class_Fee) as 'Revenue' from (
                        Select sc.SubscriptionID, 'Member Subscription' as 'ClassName',  'Member Subscription' as 'Trainer_Name', sc.SubscriptionStartDate as 'Start_Date', 
                        sc.SubscriptionEndDate as 'End_Date', sc.PaymentAmount as 'Class_Fee'
                        from Subscription sc
                        left join Member m on sc.MemberID = m.MemberID
                        Union
                        -- PT training financial
                        Select tt.ClassID, ct.ClassName, concat(tr.FirstName, ' ', tr.LastName) as 'Trainer_Name', 
                        tt.ClassDate as 'Start_Date', tt.ClassDate as 'End_Date', 50 as 'Class_Fee'
                        from Timetable tt
                        left join ClassType ct on tt.ClassCode = ct.ClassCode
                        left join Trainer tr on tt.TrainerID = tr.TrainerID
                        Where tt.ClassCode = 1) t
                        Where t.Start_Date >= %s and t.End_Date <= %s
                        Group by ClassName;"""

            total_sql_selected = """Select sum(Class_Fee) as 'Revenue' from (
                        Select sc.SubscriptionID, 'Member Subscription' as 'ClassName',  'Member Subscription' as 'Trainer_Name', sc.SubscriptionStartDate as 'Start_Date', 
                        sc.SubscriptionEndDate as 'End_Date', sc.PaymentAmount as 'Class_Fee'
                        from Subscription sc
                        left join Member m on sc.MemberID = m.MemberID
                        Union
                        -- PT training financial
                        Select tt.ClassID, ct.ClassName, concat(tr.FirstName, ' ', tr.LastName) as 'Trainer_Name', 
                        tt.ClassDate as 'Start_Date', tt.ClassDate as 'End_Date', 50 as 'Class_Fee'
                        from Timetable tt
                        left join ClassType ct on tt.ClassCode = ct.ClassCode
                        left join Trainer tr on tt.TrainerID = tr.TrainerID
                        Where tt.ClassCode = 1) t
                        Where t.Start_Date >= %s and t.End_Date <= %s"""

            single_pt_sql_selected = """Select t3.Trainer_Name, sum(Class_Fee) from (
                        Select tt.ClassID, ct.ClassName, concat(tr.FirstName, ' ', tr.LastName) as 'Trainer_Name', 
                        tt.ClassDate as 'Start_Date', tt.ClassDate as 'End_Date', 50 as 'Class_Fee'
                        from Timetable tt
                        left join ClassType ct on tt.ClassCode = ct.ClassCode
                        left join Trainer tr on tt.TrainerID = tr.TrainerID
                        Where tt.ClassCode = 1) t3
                        Where t3.Start_Date >= %s and t3.End_Date <= %s
                        group by Trainer_Name"""
        username = session["username"]

        startdate = request.form.get("startdate")
        enddate = request.form.get("enddate")

        cur1 = getCursor()
        cur1.execute(financial_sql_selected, (startdate, enddate,))
        dbcols1 = [desc[0] for desc in cur1.description]
        dbresult_sld1 = cur1.fetchall()

        cur2 = getCursor()
        cur2.execute(total_sql_selected, (startdate, enddate,))
        dbcols2 = [desc[0] for desc in cur2.description]
        dbresult_sld2 = cur2.fetchall()

        cur3 = getCursor()
        cur3.execute(single_pt_sql_selected, (startdate, enddate,))
        dbcols3 = [desc[0] for desc in cur3.description]
        dbresult_sld3 = cur3.fetchall()
        # print(dbresult_sld1)
        print(dbresult_sld3)
        return render_template("manageCheckFinancialbyDate.html",
                                username=username,
                                startdate=startdate,
                                enddate=enddate,
                                dbcols1=dbcols1,
                                dbresult_sld1=dbresult_sld1,
                               dbcols2=dbcols2,
                               dbresult_sld2=dbresult_sld2,
                               dbcols3=dbcols3,
                               dbresult_sld3=dbresult_sld3,
                            )


# Generate Member Attendance Report - summary
@app.route("/admin/gymusagereport", methods=['GET'])
def gymusagereport():
    if "username" in session:
        usage_sql = """Select opt.TypeOfVisit, sum(opt.Daily_Total) as 'NumberofMemberJoined', sum(opt.Capcity) as 'Total_Capacity', concat(convert(round(avg(opt.ratio), 2), char), '%') as 'UsageRatio'
                    from (
                    Select AT_Start_Date, TypeOfVisit, Daily_Total, Capcity, (Daily_Total/Capcity)*100 as 'ratio'
                    from (
                    Select t.Start_Date, t.End_Date, t.Purpose, count(t.ClassID) as 'Number_PT_Class', 
                    Case when t.Purpose = 'Class' then count(t.ClassID)*30
                        when t.Purpose != 'Class' then count(t.ClassID)
                        end as 'Capcity'
                    From (
                    Select tt.ClassID, tt.ClassDate as 'Start_Date', tt.ClassDate as 'End_Date', tt. ClassCode, 
                    case when tt.ClassCode = 1 then 'PT Session'
                        when tt.ClassCode != 1 then 'Class'
                        End as 'Purpose'
                    from Timetable tt) t
                    group by t.Start_Date, t.End_Date, t.Purpose) tb
                    right join (Select daily.AT_Start_Date, daily.AT_End_Date, daily.TypeOfVisit, sum(Count) 'Daily_Total' from (
                    Select DATE(at.EnterTime) as 'AT_Start_Date', DATE(at.EnterTime) as 'AT_End_Date', at.TypeOfVisit, 1 as 'Count' 
                    From Attendance at) daily
                    group by daily.AT_Start_Date, daily.AT_End_Date, daily.TypeOfVisit) atd 
                    on tb.Start_Date = atd.AT_Start_Date and tb.End_Date = atd.AT_End_Date and tb.Purpose = atd.TypeOfVisit
                    Where atd.AT_Start_Date >= '2023-01-01' and atd.AT_End_Date <= '2023-12-31'
                    ) opt
                    group by opt.TypeOfVisit;"""


        total_member_sql = """Select sum(Daily_Total) as 'Total_Member'
                    from (
                    Select t.Start_Date, t.End_Date, t.Purpose, count(t.ClassID) as 'Number_PT_Class', 
                    Case when t.Purpose = 'Class' then count(t.ClassID)*30
                        when t.Purpose != 'Class' then count(t.ClassID)
                        end as 'Capcity'
                    From (
                    Select tt.ClassID, tt.ClassDate as 'Start_Date', tt.ClassDate as 'End_Date', tt. ClassCode, 
                    case when tt.ClassCode = 1 then 'PT Session'
                        when tt.ClassCode != 1 then 'Class'
                        End as 'Purpose'
                    from Timetable tt) t
                    -- Where t.Start_Date >= '2023-02-01' and t.End_Date<= '2023-02-02'
                    group by t.Start_Date, t.End_Date, t.Purpose) tb
                    right join (Select daily.AT_Start_Date, daily.AT_End_Date, daily.TypeOfVisit, sum(Count) 'Daily_Total' from (
                    Select DATE(at.EnterTime) as 'AT_Start_Date', DATE(at.EnterTime) as 'AT_End_Date', at.TypeOfVisit, 1 as 'Count' 
                    From Attendance at) daily
                    group by daily.AT_Start_Date, daily.AT_End_Date, daily.TypeOfVisit) atd
                    on tb.Start_Date = atd.AT_Start_Date and tb.End_Date = atd.AT_End_Date and tb.Purpose = atd.TypeOfVisit
                    Where atd.AT_Start_Date >= '2023-01-01' and atd.AT_End_Date <= '2023-12-31';"""

        username = session["username"]
        cur_usage = getCursor()
        cur_usage.execute(usage_sql)
        dbcols_usage = [desc[0] for desc in cur_usage.description]
        dbresult_usage = cur_usage.fetchall()

        cur_total = getCursor()
        cur_total.execute(total_member_sql)
        dbcols_total = [desc[0] for desc in cur_total.description]
        dbresult_total = cur_total.fetchall()

        return render_template("managerGymAttendanceReport.html",
                                username=username,
                                dbcols_usage=dbcols_usage,
                                dbresult_usage=dbresult_usage,
                               dbcols_total=dbcols_total,
                               dbresult_total=dbresult_total
                                )
    else:
        return redirect(url_for("adminLogin_get"))

# Generate Member Attendance Ratio by selected period
@app.route("/admin/checkattendancebydate", methods=['POST'])
def gymusage_bydate_report():
    if "username" in session:
        usage_sql = """Select opt.TypeOfVisit, sum(opt.Daily_Total) as 'NumberofMemberJoined', sum(opt.Capcity) as 'Total_Capacity', concat(convert(round(avg(opt.ratio), 2), char), '%') as 'UsageRatio'
                    from (
                    Select AT_Start_Date, TypeOfVisit, Daily_Total, Capcity, (Daily_Total/Capcity)*100 as 'ratio'
                    from (
                    Select t.Start_Date, t.End_Date, t.Purpose, count(t.ClassID) as 'Number_PT_Class', 
                    Case when t.Purpose = 'Class' then count(t.ClassID)*30
                        when t.Purpose != 'Class' then count(t.ClassID)
                        end as 'Capcity'
                    From (
                    Select tt.ClassID, tt.ClassDate as 'Start_Date', tt.ClassDate as 'End_Date', tt. ClassCode, 
                    case when tt.ClassCode = 1 then 'PT Session'
                        when tt.ClassCode != 1 then 'Class'
                        End as 'Purpose'
                    from Timetable tt) t
                    group by t.Start_Date, t.End_Date, t.Purpose) tb
                    right join (Select daily.AT_Start_Date, daily.AT_End_Date, daily.TypeOfVisit, sum(Count) 'Daily_Total' from (
                    Select DATE(at.EnterTime) as 'AT_Start_Date', DATE(at.EnterTime) as 'AT_End_Date', at.TypeOfVisit, 1 as 'Count' 
                    From Attendance at) daily
                    group by daily.AT_Start_Date, daily.AT_End_Date, daily.TypeOfVisit) atd 
                    on tb.Start_Date = atd.AT_Start_Date and tb.End_Date = atd.AT_End_Date and tb.Purpose = atd.TypeOfVisit
                    Where atd.AT_Start_Date >= %s and atd.AT_End_Date <= %s
                    ) opt
                    group by opt.TypeOfVisit;"""


        total_member_sql = """Select sum(Daily_Total) as 'Total_Member'
                    from (
                    Select t.Start_Date, t.End_Date, t.Purpose, count(t.ClassID) as 'Number_PT_Class', 
                    Case when t.Purpose = 'Class' then count(t.ClassID)*30
                        when t.Purpose != 'Class' then count(t.ClassID)
                        end as 'Capcity'
                    From (
                    Select tt.ClassID, tt.ClassDate as 'Start_Date', tt.ClassDate as 'End_Date', tt. ClassCode, 
                    case when tt.ClassCode = 1 then 'PT Session'
                        when tt.ClassCode != 1 then 'Class'
                        End as 'Purpose'
                    from Timetable tt) t
                    -- Where t.Start_Date >= '2023-02-01' and t.End_Date<= '2023-02-02'
                    group by t.Start_Date, t.End_Date, t.Purpose) tb
                    right join (Select daily.AT_Start_Date, daily.AT_End_Date, daily.TypeOfVisit, sum(Count) 'Daily_Total' from (
                    Select DATE(at.EnterTime) as 'AT_Start_Date', DATE(at.EnterTime) as 'AT_End_Date', at.TypeOfVisit, 1 as 'Count' 
                    From Attendance at) daily
                    group by daily.AT_Start_Date, daily.AT_End_Date, daily.TypeOfVisit) atd
                    on tb.Start_Date = atd.AT_Start_Date and tb.End_Date = atd.AT_End_Date and tb.Purpose = atd.TypeOfVisit
                    Where atd.AT_Start_Date >= %s and atd.AT_End_Date <= %s;"""

        username = session["username"]
        startdate = request.form.get("startdate")
        enddate = request.form.get("enddate")

        cur_u1 = getCursor()
        cur_u1.execute(usage_sql, (startdate, enddate,))
        dbcols_u1 = [desc[0] for desc in cur_u1.description]
        dbresult_u1 = cur_u1.fetchall()

        cur_to = getCursor()
        cur_to.execute(total_member_sql, (startdate, enddate,))
        dbcols_to = [desc[0] for desc in cur_to.description]
        dbresult_to = cur_to.fetchall()

        return render_template("managerGymAttendanceReportByDate.html",
                                username=username,
                                dbcols_u1=dbcols_u1,
                                dbresult_u1=dbresult_u1,
                                dbcols_to=dbcols_to,
                                dbresult_to=dbresult_to
                                )
    else:
        return redirect(url_for("adminLogin_get"))


#Add Member Page    
@app.route("/admin/member/addmember")
def addmember():
    if "username" in session:
        username = session["username"]
        return render_template("addmember.html"
                                ,username=username
                                )
    else:
        return redirect(url_for("adminLogin_get"))


@app.route("/admin/member/editmember/process",methods=["POST"])   
def editMemberProcess():
    if "username" in session:
        username = session["username"]
        #get userinput member details
        memberID=request.form['memberID']
        firstname=request.form['firstname']
        lastname=request.form['lastname']
        email=request.form['email']
        phone=request.form['phone']
        PhysicalAddress=request.form['PhysicalAddress']
        DOB=request.form['DOB']
        EmergencyName=request.form['EmergencyName']
        EmergencyNumber=request.form['EmergencyNumber']
        Mconditions=request.form['Mconditions']
        GJD=request.form['GJD']
        psw=request.form['psw']
        ReceivingNotifications=request.form['ReceivingNotifications']
        autoFee=request.form['autoFee']
        BankName=request.form['BankName']
        BankAccountHolderName=request.form['BankAccountHolderName']
        BankAccountNumber=request.form['BankAccountNumber']
        MemberStatus=request.form['MemberStatus']
        MemberNotes=request.form['MemberNotes']
        #Add member process
        if memberID=="None":
            cur=getCursor()
            sql="""INSERT INTO MEMBER (FirstName, LastName, Email, PhysicalAddress, Phone, DateOfBirth, EmergencyContactName, EmergencyContactNumber,
                        MedicalConditions, GymJoinDate, ReceivingNotifications, MemberPassword, AuthorityOnCollectingFees, BankName, BankAccountHolderName, BankAccountNumber, MemberStatus,MemberNotes)
                        VALUES(%s, %s, %s, %s, %s, %s, %s, %s,%s, %s, %s,%s, %s,%s, %s, %s, %s,%s)"""
            cur.execute(sql,(firstname,lastname,email,PhysicalAddress,phone,DOB,EmergencyName,EmergencyNumber,Mconditions,GJD,ReceivingNotifications,psw,autoFee,BankName,BankAccountHolderName,BankAccountNumber,MemberStatus,MemberNotes))
            #render the added new-member detail page
            cur=getCursor()
            cur.execute("select * from Member where email=%s",(email,))
            dbcols=[desc[0] for desc in cur.description]
            dbresult=cur.fetchall()
            #assign memberID variable for later use
            memberID=dbresult[0][0]
            flash("New member has been added successfully!", "successadd")

            return redirect(f"/admin/member/editmember?memberID={memberID}")
        #update member detail process    
        else:
            cur=getCursor()
            sql="""update Member set FirstName=%s, LastName=%s, Email=%s, PhysicalAddress=%s, Phone=%s, DateOfBirth=%s,
                    EmergencyContactName=%s, EmergencyContactNumber=%s, MedicalConditions=%s, GymJoinDate=%s, ReceivingNotifications=%s,
                    MemberPassword=%s, AuthorityOnCollectingFees=%s, BankName=%s, BankAccountHolderName=%s, BankAccountNumber=%s, MemberStatus=%s,MemberNotes=%s
                    where MemberID=%s"""
            cur.execute(sql,(firstname,lastname,email,PhysicalAddress,phone,DOB,EmergencyName,EmergencyNumber,Mconditions,GJD,ReceivingNotifications,psw,autoFee,BankName,
                             BankAccountHolderName,BankAccountNumber,MemberStatus,MemberNotes,memberID))
            flash("Details have been updated successfully!", "success")
            
            return redirect(f"/admin/member/editmember?memberID={memberID}")
            # #render the the same member page with same memberID
            # cur.execute("select * from Member where MemberID=%s",(memberID,))
            # dbcols=[desc[0] for desc in cur.description]
            # dbresult=cur.fetchall()
            # successMessage_update="Details have been successfully updated"
            # return render_template("membereach.html"
            #                         ,username=username,
            #                         dbcols=dbcols,
            #                         dbresult= dbresult,
            #                         successMessage_update=successMessage_update
            #                         )
    else:
        return redirect(url_for("adminLogin_get"))
   

   


# #Individual member detail page   
# @app.route("/admin/member/each",methods=["POST"]) 
# def eachmemberdetail():
#     if "username" in session:
#         username = session["username"]
#         memberID=request.form["memberID"]
#         cur=getCursor()
#         cur.execute("select * from Member where MemberID=%s",(memberID,))
#         dbcols=[desc[0] for desc in cur.description]
#         dbresult=cur.fetchall()
     
#         return render_template("membereach.html",
#                                 username=username,
#                                 dbcols=dbcols,
#                                  dbresult= dbresult,
#                                  memberID=memberID
#                                 )
#     else:
#         return redirect(url_for("adminLogin_get"))


# Edit member details page with original member detail data.    
@app.route("/admin/member/editmember")
def editMember():
    if "username" in session:
        username = session["username"]
        memberID=request.args.get("memberID")
        removeReadonly=request.args.get("removeReadonly","")
        cur=getCursor()
        cur.execute("select * from Member where MemberID=%s",(memberID,))
        dbresult=cur.fetchall()
        #assign the originial values to variables
        firstname=dbresult[0][1]
        lastname=dbresult[0][2]
        email=dbresult[0][3]
        phone=dbresult[0][5]
        PhysicalAddress=dbresult[0][4]
        DOB=dbresult[0][6]
        EmergencyName=dbresult[0][7]
        EmergencyNumber=dbresult[0][8]
        Mconditions=dbresult[0][9]
        GJD=dbresult[0][10]
        psw=dbresult[0][12]
        ReceivingNotifications=dbresult[0][11]
        autoFee=dbresult[0][13]
        BankName=dbresult[0][14]
        BankAccountHolderName=dbresult[0][15]
        BankAccountNumber=dbresult[0][16]
        MemberStatus=dbresult[0][17]
        MemberNotes=dbresult[0][18]
        # print(bool(ReceivingNotifications=='Yes'))
        # print(bool(ReceivingNotifications=='No'))
        # print(bool(autoFee=='Yes'))
        # print(bool(autoFee=='No'))
        # print(bool(MemberStatus=='Active'))
        # print(bool(MemberStatus=='Inactive'))
        return render_template("editmember.html",
                                memberID= memberID,
                                username=username,
                                firstname=firstname,
                                lastname=lastname,
                                email=email,
                                phone=phone,
                                PhysicalAddress=PhysicalAddress,
                                DOB=DOB,
                                EmergencyName=EmergencyName,
                                EmergencyNumber=EmergencyNumber,
                                Mconditions=Mconditions,
                                GJD=GJD,
                                psw=psw,
                                ReceivingNotifications=ReceivingNotifications,
                                autoFee=autoFee,
                                BankName=BankName,
                                BankAccountHolderName=BankAccountHolderName,
                                BankAccountNumber=BankAccountNumber,
                                MemberStatus=MemberStatus,
                                MemberNotes=MemberNotes,
                                removeReadonly=removeReadonly
                                )
    else:
        return redirect(url_for("adminLogin_get"))   
    
    
@app.route("/admin/trainer")
def manageTrainer():
    if "username" in session:
        username = session["username"]
        cur=getCursor()
        cur.execute("""SELECT TrainerID, FirstName, LastName, Email, Phone, DateOfBirth, DateOfEmployment,
                    TrainerStatus FROM LincolnGym.Trainer;""")
        dbcols=[desc[0] for desc in cur.description]
        dbresult=cur.fetchall()
        return render_template("manageTrainer.html",
                            dbcols=dbcols,
                            dbresult=dbresult
                                ,username=username
                                )        

    else:
        return redirect(url_for("adminLogin_get"))
     

    
# Edit trainer details page with original trainer detail data.    
@app.route("/admin/trainer/edittrainer")
def editTrainer():
    print("##endittrainer endpoint")
    if "username" in session:
        print("##endittrainer args", request.args)
        removeReadonly=request.args.get("removeReadonly","")
        username = session["username"]
        trainerID=request.args.get("trainerID")
        cur=getCursor()
        cur.execute("select * from Trainer where TrainerID=%s",(trainerID,))
        dbresult=cur.fetchall()
        #assign the originial values to variables
        print("##debug select * from Trainer where TrainerID=%s",(trainerID,))
        print("##dbresult", dbresult[0])
        firstname=dbresult[0][1]
        lastname=dbresult[0][2]
        email=dbresult[0][3]
        phone=dbresult[0][4]
        #PhysicalAddress=dbresult[0][4]
        DOB=dbresult[0][5]
        #EmergencyName=dbresult[0][7]
        #EmergencyNumber=dbresult[0][8]
        #Mconditions=dbresult[0][9]
        DOE=dbresult[0][6]
        psw=dbresult[0][7]
        #ReceivingNotifications=dbresult[0][11]
        #autoFee=dbresult[0][13]
        EmergencyName=dbresult[0][8]
        EmergencyNumber=dbresult[0][9]
        Mconditions=dbresult[0][10]
        TrainerStatus=dbresult[0][-1]
        #MemberNotes=dbresult[0][18]
        # print(bool(ReceivingNotifications=='Yes'))
        # print(bool(ReceivingNotifications=='No'))
        # print(bool(autoFee=='Yes'))
        # print(bool(autoFee=='No'))
        # print(bool(MemberStatus=='Active'))
        # print(bool(MemberStatus=='Inactive'))
        print("##endittrainer render_template")
        return render_template("edittrainer.html",
                                trainerID=trainerID,
                                username=username,
                                firstname=firstname,
                                lastname=lastname,
                                email=email,
                                phone=phone,
                                #PhysicalAddress=PhysicalAddress,
                                DOB=DOB,
                                EmergencyName=EmergencyName,
                                EmergencyNumber=EmergencyNumber,
                                Mconditions=Mconditions,
                                DOE=DOE,
                                psw=psw,
                                #ReceivingNotifications=ReceivingNotifications,
                                #autoFee=autoFee,
                                #BankName=BankName,
                                #BankAccountHolderName=BankAccountHolderName,
                                #BankAccountNumber=BankAccountNumber,
                                TrainerStatus=TrainerStatus,
                                #MemberNotes=MemberNotes
                                removeReadonly=removeReadonly
                                )
    else:
        return redirect(url_for("adminLogin_get"))



@app.route("/admin/trainer/edittrainer/process",methods=["POST"])   
def editTrainerProcess():
    print("1")
    if "username" in session:
        username = session["username"]
        #get userinput member details
        trainerID=request.form['trainerID']
        firstname=request.form['firstname']
        lastname=request.form['lastname']
        email=request.form['email']
        phone=request.form['phone']
        DOB=request.form['DOB']
        DOE=request.form['DOE']
        psw=request.form['psw']
        trainerStatus=request.form['trainerStatus']
        print("addtrainerstatus:",trainerStatus)
        EmergencyName=request.form['EmergencyName']
        EmergencyNumber=request.form['EmergencyNumber']
        Mconditions=request.form['Mconditions']
        
        #Add trainer process

        if trainerID=="None":
            #print("3")
            cur=getCursor()
            sql="""INSERT INTO lincolngym.Trainer( FirstName, LastName, Email, Phone, DateOfBirth, DateOfEmployment, TrainerPassword, EmergencyContactName, EmergencyContactNumber, MedicalConditions, TrainerStatus)
                    values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
            cur.execute(sql,(firstname,lastname,email,phone,DOB,DOE,psw,EmergencyName,EmergencyNumber,Mconditions,trainerStatus))
            #render the added new-trainer detail page
            cur=getCursor()
            cur.execute("select * from Trainer where email=%s",(email,))
            dbcols=[desc[0] for desc in cur.description]
            dbresult=cur.fetchall()
            #assign memberID variable for later use
            trainerID=dbresult[0][0]
            flash("New trainer has been successfully added!", "successAddTrainer")
            return redirect(f"/admin/trainer/edittrainer?trainerID={trainerID}")
        #update trainer detail process
        else:
            #print("4")
            cur=getCursor()
            sql="""update Trainer set FirstName=%s, LastName=%s, Email=%s, Phone=%s, DateOfBirth=%s,
            DateOfEmployment=%s, TrainerPassword=%s, EmergencyContactName=%s, EmergencyContactNumber=%s, MedicalConditions=%s, TrainerStatus=%s
            where TrainerID=%s"""
            cur.execute(sql,(firstname,lastname,email,phone,DOB,DOE,psw,EmergencyName,EmergencyNumber,Mconditions,trainerStatus,trainerID))
            #render the the same trainer page with same trainerID
            cur.execute("select * from Trainer where TrainerID=%s",(trainerID,))
            flash("Details have been updated successfully!", "success")
            # dbcols=[desc[0] for desc in cur.description]
            # dbresult=cur.fetchall()
            # successMessage_update="Details have been successfully updated"
            # print(successMessage_update)
            return redirect(f"/admin/trainer/edittrainer?trainerID={trainerID}")
                # render_template("edittrainer.html"
                #                     ,username=username,
                #                     dbcols=dbcols,
                #                     dbresult= dbresult,
                #                     successMessage_update=successMessage_update
                #                     )
    else:
        #print("5")
        return redirect(url_for("adminLogin_get"))


#Add a trainer page    
@app.route("/admin/addtrainer") 
def addtrainer():
    if "username" in session:
        username = session["username"]
        
        return render_template("addtrainer.html",
                                username=username
                                )        
    else:
        return redirect(url_for("adminLogin_get"))
#view trainer class page
@app.route("/admin/viewTrainerClass") 
def viewTrainerClass():
    if "username" in session:
        username = session["username"]
        
        return render_template("viewTrainerClass.html",
                                username=username
                                )        
    else:
        return redirect(url_for("adminLogin_get"))
    
           
    
    
@app.route("/admin/weeklyUpdate")
def weeklyUpdate():
    if "username" in session:
        username = session["username"]
        return render_template("weeklyUpdate.html",username=username)
    else:
        return redirect(url_for("adminLogin_get"))
@app.route("/admin/weeklyUpdatePOST",methods=["POST"]) 
def weeklyUpdatePOST():
    topic = request.form.get("topic")
    content = request.form.get("content")
    cur=getCursor()
    sql = """INSERT INTO weeklyupdate (topic,content)
    VALUES (%s,%s) """
    cur.execute(sql, (topic,content))
    flash(" You have sent a weekly update to members successfully!")
    return redirect(url_for("weeklyUpdate"))
    

#trainer interface
@app.route("/trainer/myProfile")
def trainer():
    if "username" in session:
        username = session["username"]     
        cur=getCursor()
        sql_trainer = """SELECT * FROM trainer WHERE Email = %s """
        # has to add "," to make it a tuple
        para= (username,)
        cur.execute(sql_trainer,para)
        trainer = cur.fetchall()
        trainer_id = trainer[0][0]
        month = request.args.get('month')
        # only show selected month data
        if month :
            sql_timetable = """SELECT classtype.ClassName, timetable.ClassDate,timetable.StartTime,timetable.EndTime
                            FROM timetable
                            INNER JOIN classtype ON classtype.ClassCode = timetable.ClassCode
                             WHERE TrainerID = %s
                             AND  MONTH(timetable.ClassDate) = %s
                             ORDER BY timetable.ClassDate;  """
            cur.execute(sql_timetable,(trainer_id, month))
        else: 
            sql_timetable = """SELECT classtype.ClassName, timetable.ClassDate,timetable.StartTime,timetable.EndTime
                            FROM timetable
                            INNER JOIN classtype ON classtype.ClassCode = timetable.ClassCode
                             WHERE TrainerID = %s 
                             ORDER BY timetable.ClassDate;  """
            cur.execute(sql_timetable,(trainer_id,))
        timetable = cur.fetchall()
        months = []
        for rows in timetable:
            date = rows[1]
            # print(date)
            datestring = str(date)
            dateStringList = datestring.split('-')
            months.append(dateStringList[1])
        filteredMonths = list(dict.fromkeys(months))
        # print(filteredMonths)

        return render_template("trainer.html",username=username, trainer=trainer, timetable=timetable, filteredMonths=filteredMonths, trainer_id=trainer_id)
    else:
        return redirect(url_for("trainerLogin"))
   
#trainer login 
@app.route("/trainer",methods=["POST", "GET"])
def trainerLogin():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        error = ""
        cur=getCursor()
        sql = """SELECT * FROM trainer WHERE Email = %s AND TrainerPassword = %s """
        cur.execute(sql, (email,password))
        trainer = cur.fetchall()
        if len(trainer) == 1:
            trainerID = trainer[0][0]
            session["userID"] = trainerID
            session["username"] = email
            if trainer[0][11] == "Active":
                return redirect(url_for("trainer"))
            else:
                flash("Your profile has been archived.Please contact the gym manager!")
                return render_template("trainerLogin.html")
        else:
            flash("Invalid email or password!")
            return render_template("trainerLogin.html", error=error)   
    return render_template("trainerLogin.html")
# trainer update
@app.route("/trainerUpdate",methods=["POST"])
def trainerUpdate():
    phone = request.form.get("phone")
    contactName = request.form.get("contactName")
    contactPhone = request.form.get("contactPhone")
    cur=getCursor()
    sql = """UPDATE trainer SET Phone = %s, EmergencyContactName = %s, EmergencyContactNumber=%s """
    cur.execute(sql, (phone,contactName,contactPhone))
    flash("Update successful!")
    return redirect(url_for("trainer"))

# trainer password reset function
@app.route("/trainerPWReset", methods=["POST"])
def trainer_password_reset():
    password = request.form.get("password")
    confirmPassword = request.form.get("confirmPassword")
    email = session["username"]
    cur=getCursor()
    # new password has to be at leat 8 characters
    if len(password)>7 and (password==confirmPassword):
        sql = """UPDATE trainer SET TrainerPassword = %s WHERE Email = %s """
        cur.execute(sql, (password, email))
        flash("Password reset succeed, please login with new password!")
        return render_template("trainerLogin.html")
    else:
        flash("Error! Please reset again!")
        return redirect(url_for("trainer"))  
# trainer/myTrainee section
@app.route("/trainer/myTrainee")
def myTrainee():
    if "username" in session:
        username = session["username"]    
        cur=getCursor()
        cur.execute("SELECT trainer.TrainerID FROM trainer where trainer.Email=%s",(username,))
        TrainerID = cur.fetchone()
        # the SQL query has returned a tuple, the TrainerID is extracted from the tuple below
        TrainerID =TrainerID[0]
        cur=getCursor()
        #the mySQL query below identifies all PT session bookings for the logged in trainer that occur today or in the future
        cur.execute("SELECT member.MemberID, member.FirstName, member.LastName, member.DateOfBirth, member.MemberNotes, booking.ClassID, timetable.TrainerID, timetable.ClassCode, timetable.ClassDate \
        FROM member \
        JOIN booking ON member.MemberID=booking.MemberID \
        JOIN timetable ON booking.ClassID=timetable.ClassID \
        WHERE (timetable.ClassCode=1 AND timetable.TrainerID=%s AND timetable.ClassDate >=CURDATE()) ORDER BY member.LastName, member.FirstName, member.MemberID, timetable.ClassDate;", (TrainerID,)) 
        TraineesDetails = cur.fetchall()        
        #convert TraineesDetails from list of tuples to list of lists so DateOfBirth can be replaced with trainee's age
        List_TraineesDetails = [list(ele) for i,ele in enumerate(TraineesDetails)]                
        #the loop below uses each trainee's date of birth to calculate their age, then replaces their DateOfBirth with their age
        for x in List_TraineesDetails:
            DateOfBirth=(x[3])
            today=date.today()
            age = relativedelta(today, DateOfBirth).years
            x[3]=age  
        #convert lists of lists back into a list of tuples  
        tuples=[]
        for x in List_TraineesDetails:
            tuples.append(tuple(x))           
        TraineesDetails=tuples      
        return render_template("myTrainee.html",TraineesDetails=TraineesDetails, username=username)
    else:
        return redirect(url_for("trainerLogin"))
