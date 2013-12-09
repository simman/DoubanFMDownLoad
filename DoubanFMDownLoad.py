# coding=utf8
#!/usr/bin/env python
############################
# 
#  豆瓣FM音乐批量下载 Python 脚本
#
#  __author__ = '李伟'
############################
import os
import urllib2
import json
import time
import MySQLdb
import sys
import hashlib
#中文乱码
reload(sys)
sys.setdefaultencoding( "utf-8" )

# 配置信息
downLoadPath = './upload/'  #下载路径
tmpFileName = 'tempfje_-DSK8FJ2Flkjs8ffsSS.txt'
mp3FileName = 'songlist.txt'
channelUrl = 'http://www.douban.com/j/app/radio/channels'   #专辑URL
songsListUrl = 'http://douban.fm/j/mine/playlist?type=n&channel='  #歌曲URL
album_download_num = 20 #每张专辑获取多少首数据


#####################################
#
#   获取音乐列表的JSON数据，并写入文件
#
#####################################
def get_music_json(albumid):
    
    url = songsListUrl + str(albumid)
    music_json = urllib2.urlopen(url)    
    base_json = json.load(music_json)   
    output = open(tmpFileName, 'a')  # 增量写入txt
    for i in base_json['song']:     # 找到json中的相关元素
        aid = i['aid'].encode('utf8')
        albumtitle = i['albumtitle'].encode('utf8')
        artist = i['artist'].encode('utf8')
        company = i['company'].encode('utf8')
        kbps = i['kbps'].encode('utf8')
        lengths = i['length']
        picture = i['picture'].encode('utf8')
        public_time = i['public_time']
        rating_avg = i['rating_avg']
        sid = i['sid'].encode('utf8')
        title = i['title'].encode('utf8')
        url = (hashlib.md5(i['sid']).hexdigest().upper())
        fromurl = i['url'].encode('utf8')
        output.write(('%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s' % (aid, albumtitle, artist, company, kbps, lengths, picture, public_time, rating_avg,sid, title, url, fromurl)) + '\t\n')
    output.close()

#####################################
#
#   重复数据处理
#
#####################################
def no_repeat():
    # 对临时txt去重并排序
    read_txt = file(tmpFileName, 'r')    # 读临时txt
    write_txt = file(mp3FileName, 'w')   # 要写入的txt
    s = set()   # 用set去重
    for i in read_txt:  # 把txt写到set过的变量中
        s.add(i)
    s = list(s)     # 先转成列表才能排序
    s.sort()        # 排序
    for i in s:     # 写入txt
        i = i.replace('/', '&')
        write_txt.write(i)
    os.remove(tmpFileName)   # 删除临时txt

#####################################
#
#   从文件读出数据
#
####################################
def get_music_file(album_id):
    songFile = open(mp3FileName, 'r');
    sf = songFile.readlines();
    for v in sf:
        insertOneData(v.split('\t'), album_id)
    os.remove(mp3FileName)   # 删除文件
#####################################
#
#   数据库处理
#
#####################################

# 插入一条数据
def insertOneData(arr, channel_id):

    conn = get_db_connect()
    cursor = conn.cursor()
    sql = "insert into fm_songs(aid,albumtitle,artist,company,kbps,lengths,picture,public_time,rating_avg,sid,name,url,fromurl,channel_id) value(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    param = (arr[0],arr[1],arr[2],arr[3],arr[4],arr[5],arr[6],arr[7],arr[8],arr[9],arr[10],arr[11],arr[12],channel_id)

    n = cursor.execute(sql, param)
    conn.commit()
    if n:
        print arr[9] + '成功插入'
    else:
        print arr[9] + '插入数据失败' + param
    #关闭
    cursor.close()
    conn.close()


# 获取专辑列表
def get_album_list():
    album_json = urllib2.urlopen(channelUrl)
    base_json = json.load(album_json)

    conn = get_db_connect()
    cursor = conn.cursor()
    sql = "insert into fm_channel(channel_en, channel_id, channel_name, name_en, sort_id) value(%s, %s, %s, %s, %s)"

    v_list = []
    for i in base_json['channels']:
        channel_en = i['abbr_en'].encode('utf8')
        channel_id = i['channel_id']
        channel_name = i['name'].encode('utf8')
        name_en = i['name_en'].encode('utf8')
        sort_id = i['seq_id']
        v = (str(channel_en), channel_id, str(channel_name), str(name_en), sort_id)
        if len(channel_en) != 0:    # 如果数据为空
            v_list.append(v)
    n = cursor.executemany(sql, v_list)
    conn.commit()
    if n:
        print '专辑数据获取成功'
    else:
        print '专辑数据获取失败'
    #关闭
    cursor.close()
    conn.close()
    return v_list

# 遍历下载，暂未用多线程
def downLoadMp3(s):
    print '系统正在载入下载列表...'
    for k, v in enumerate(s):
        mp3Name = downLoadPath + v[11] + '.mp3'
        # 判断文件是否存在
        file_is_exists = os.path.exists(mp3Name)
        if not file_is_exists :
            d = v[13].replace('&', '/')
            re = urllib2.Request(d)
            rs = urllib2.urlopen(re).read()
            open(mp3Name, 'wb').write(rs)
            m = 'Title: %s 下载完成... (已经下载了： %s 首歌曲)'
            value = (v[2], k+1)
            print m % value
            update_songs_download_status(v[0])
        time.sleep(1)

# 更新歌曲下载状态
def update_songs_download_status(songs_id):
    conn = get_db_connect()
    cursor = conn.cursor()
    sql = "update fm_songs set is_download = 1 where id = %s"
    param = (songs_id)
    n = cursor.execute(sql, param)
    conn.commit()
    cursor.close()
    conn.close()

# 获取所有音乐
def get_all_songs():
    conn = get_db_connect()
    cursor = conn.cursor()
    n = cursor.execute("select * from fm_songs where is_download = 0")
    s = cursor.fetchall()
    cursor.close()
    conn.close()
    return s
def get_db_connect():
    conn=MySQLdb.connect(host="localhost",user="root",passwd="rootpic",db="Class_11_Team_FivePLX",charset="utf8")
    return conn

def main():
    # # 获取所有的专辑
    # v_list = get_album_list()
    # # 开始遍历每个专辑下的歌曲列表
    # for v_i in v_list:
    #     for i in range(0, album_download_num / 10):
    #         get_music_json(v_i[1])
    #         print '已经抓取了' + str(i * 10) + '首数据...'
    #         time.sleep(1)   # 延时1秒
    #     no_repeat()     # 去重排序
    #     print '抓取' + v_i[2] +'频道音乐列表完成'
    #     # 对抓到的歌曲进行入库操作
    #     get_music_file(v_i[1])
    #     print v_i[2] + '数据已经入库，等待3秒开始下张专辑获取'
    #     time.sleep(3)

    #开始下载歌曲
    s = get_all_songs()
    downLoadMp3(s)


main()
