#!/usr/bin/python
'''
- Bulk export downloaded audios in Ximalaya.
- Auto rename exported audios using a configurable format.
- Create folders for albums, named using album names, and save audios correspondingly.

# Copyright 2016 Guang-zhi XU
#
# This file is distributed under the terms of the
# GPLv3 licence. See the LICENSE file for details.
# You may use, distribute and modify this code under the
# terms of the GPLv3 license.

Update time: 2016-07-12 11:18:42.
'''

__version__='XimaExport v1.0'

#----------------------Import----------------------
import sys,os
import shutil
import pandas as pd
import sqlite3
import argparse
from lib.tools import printHeader, printInd, printNumHeader
from lib import tools
from urllib import urlretrieve
try:
    import mutagen
    HAS_MUTAGEN=True
except:
    HAS_MUTAGEN=False

if sys.version_info[0]>=3:
    #---------------------Python3---------------------
    from urllib.parse import unquote
    from urllib.parse import urlparse
else:
    #--------------------Python2.7--------------------
    from urllib import unquote
    from urlparse import urlparse






#-------Fetch a column from pandas dataframe-------
fetchField=lambda x, f: x[f].unique().tolist()



def convertPath(url):
    '''Convert a url string to an absolute path
    This is necessary for filenames with unicode strings.
    '''

    url=tools.enu(url)
    path=os.path.abspath(url)

    return path


#--------------Get album id and name list in database----------------
def getAlbumList(df,album,verbose=True):
    '''Get album id and name list in database

    <album>: select album from database.
              If None, select all albums.
              If str, select album <album>.

    Return: <result>: list, with elements of (id, album_name).

	Update time: 2016-07-12 11:36:07.
    '''

    #-----------------Get all albums-----------------
    allids=fetchField(df,'albumId')

    #---------------Select target album---------------
    if album is None:
        ids=allids
    if type(album) is str or type(album) is unicode:
        seldf=df[df.albumName==album]
        ids=fetchField(seldf,'albumId')

	#--------------------Get names--------------------
    result=[]
    for ff in ids:
        result.append([ff,df[df.albumId==ff].albumName.iloc[0]])

    #----------------------Return----------------------
    if album is None:
        return result
    else:
        if len(result)==0:
            print("Given album name not found in database.")
            return []
        else:
            return result


#------------------------Get tables from sqlite------------------------
def getData(db,verbose=True):

    query=\
    '''SELECT download_table.rowid,
          download_table.title,
          download_table.trackId,
          download_table.artist,
          download_table.likes,
          download_table.duration,
          download_table.createTime,
          download_table.downloadUrl,
          download_table.downloadAacUrl,
          download_table.downloadedBytes,
          download_table.totalBytes,
          download_table.filepath,
          download_table.albumId,
          download_table.albumName,
          download_table.albumImage
       FROM download_table
    '''

    ret=db.execute(query)
    data=ret.fetchall()
    df=pd.DataFrame(data=data,columns=['rowid','title','trackId',\
        'artist','likes','duration','createTime','downloadUrl',\
        'downloadAacUrl','downloaded','totalBytes','filepath','albumId',\
        'albumName','albumImage'])

    return df



#-------------------Write ID3 metadata to audio file-------------------
def writeMeta(filename,meta,verbose=True):
    '''Write ID3 metadata to audio file

    <filename>: str, abspath to audio file.
    <meta>: dict, metadata dict.

    Write metadata into the .mp3 audio file using ID3

    Update time: 2016-07-12 14:09:27.
    '''

    from mutagen.mp3 import MP3
    from mutagen.mp4 import MP4, MP4Cover
    from mutagen.id3 import ID3, APIC, error

    audio=mutagen.File(filename)

    #------------Add ID3 tag if not exists------------
    try:
        audio.add_tags()
    except:
        pass

    for kk,vv in meta.items():
        if kk=='cover':
            #------------------For mp3 format------------------
            #ap=APIC(encoding=3, mime=tools.deu(vv),type=3,\
            #desc=u'Cover',data=open(vv,'rb').read())
            #audio.tags.add(ap)

            #------------------For mp4 format------------------
            ap2=MP4Cover(open(vv,'rb').read(),\
                imageformat=MP4Cover.FORMAT_JPEG)
            audio['covr']=[ap2]
        else:
            audio[kk]=tools.deu(vv)
    
    audio.save()

    return


	


#----------------------Process files in an album----------------------
def processAlbum(df,indir,outdir,albumid,verbose=True):
    '''Process files in an album

    '''
    seldf=df[df.albumId==albumid]
    albumname=seldf.iloc[0].albumName
    ids=seldf.rowid
    faillist=[]
    metafaillist=[]

    subfolder=os.path.join(outdir,albumname)
    subfolder=convertPath(subfolder)
    if not os.path.isdir(subfolder):
        try:
            os.makedirs(subfolder)
        except:
            if verbose:
                printInd('Failed to create subfolder %s' %albumname,2)
                printInd('Skip folder %s' %albumname,2)
            faillist.extend(fetchField(df,'title'))
            return faillist,metafaillist

    #------------Download album cover image------------
    albumImage=seldf.iloc[0].albumImage
    try:
        coverimg=os.path.join(subfolder,'cover.jpg')
        imgfile=urlretrieve(albumImage,coverimg)[0]
        got_cover=True
    except:
        got_cover=False

    #----------------Loop through files----------------
    for ii in range(len(ids)):
        title=seldf.iloc[ii].title
        artist=seldf.iloc[ii].artist
        downloaded=seldf.iloc[ii].downloaded
        totalBytes=seldf.iloc[ii].totalBytes
        downloadurl1=seldf.iloc[ii].downloadUrl
        downloadurl2=seldf.iloc[ii].downloadAacUrl
        filepath=seldf.iloc[ii].filepath

        tmpfile=False
        gotfile=False

        newname='%s-%s.mp3' %(title,artist)
        newname=os.path.join(tools.deu(subfolder),newname)
        newname=convertPath(newname)

        if verbose:
            printInd('Getting file for: %s' %title, 2)

        #-----If imcomplete download, try downloading now-----
        if downloaded<totalBytes:
            tmpfile=True
            if verbose:
                printInd('Downloading imcomplete audio:',2)
                printInd(title,2)
            try:
                tmpfile=urlretrieve(downloadurl1,newname)
                gotfile=True
            except:
                tmpfile=urlretrieve(downloadurl2,newname)
                gotfile=True
            finally:
                if verbose:
                    printInd('Failed to download %s' %title,2)
                faillist.append(title)
                gotfile=False
        else:
            gotfile=True

        if not gotfile:
            continue

        #----------------------Export----------------------
        if not tmpfile:

            filename=os.path.join(indir,'Download')
            filename=os.path.join(filename,filepath)

            if os.path.exists(filename):
                try:
                    shutil.copy2(filename,newname)
                except:
                    if verbose:
                        printInd('Failed to copy file %s' %title,2)
                        faillist.append(title)
                    continue

        #------------Write metadata (optional)------------
        if HAS_MUTAGEN:

            if verbose:
                printInd('Writing metadata for: %s' %title, 2)

            #--------------------mp3 format--------------------
            meta={'title':title, 'artist': artist, 'album': albumname,\
                  'comments': 'Exported from Ximalaya by XimaExport'}
            #--------------------mp4 format--------------------
            meta={'\xa9nam':title, '\xa9ART': artist, '\xa9alb': albumname,\
                  'comments': 'Exported from Ximalaya by XimaExport'}
            if got_cover:
                meta['cover']=imgfile

            try:
                writeMeta(newname,meta)
            except:
                metafaillist.append(title)


    return faillist,metafaillist



	


#-----------------------Main-----------------------
def main(dbfile,outdir,album,verbose):

    try:
        db = sqlite3.connect(dbfile)
        if verbose:
            printHeader('Connected to database:')
            printInd(dbfile,2)
    except:
        printHeader('Failed to connect to database:')
        printInd(dbfile)
        return 1

    #--------------------Fetch data--------------------
    df=getData(db)
    indir=os.path.split(os.path.abspath(dbfile))[0]

    #----------------Get album list----------------
    albumlist=getAlbumList(df,album)
    if len(albumlist)==0:
        return 1

    #----------Create output dir if not exist----------
    if not os.path.isdir(outdir):
        try:
            os.makedirs(outdir)
        except:
            printHeader('Failed to create output directory: %s' %outdir)
            return 1

    #---------------Loop through albums---------------
    faillist=[]
    metafaillist=[]

    for ii,albumii in enumerate(albumlist):
        idii,albumnameii=albumii
        if verbose:
            printNumHeader('Processing album: "%s"' %albumnameii,\
                ii+1,len(albumlist),1)
        failistii,metafaillistii=processAlbum(df,indir,outdir,idii,verbose)
        faillist.extend(failistii)
        metafaillist.extend(metafaillistii)

    #-----------------Close connection-----------------
    if verbose:
        printHeader('Drop connection to database:')
    db.close()

    #------------------Print summary------------------
    faillist=list(set(faillist))
    metafaillist=list(set(metafaillist))

    printHeader('Summary',1)
    if len(faillist)>0:
        printHeader('Failed to export:',2)
        for failii in faillist:
            printInd(failii,2)

    if len(metafaillist)>0:
        printHeader('Failed to write meta data in:',2)
        for failii in metafaillist:
            printInd(failii,2)

    if len(faillist)==0 and len(metafaillist)==0:
        printHeader('All done.',2)

    return 0




#-----------------------Main-----------------------
if __name__=='__main__':

    parser=argparse.ArgumentParser(description='Export audios from Ximalaya.')

    parser.add_argument('dbfile',type=str,\
            help='Path to the "ting.sqlite" database file.')
    parser.add_argument('outdir',type=str,\
            help='Output folder to save exported files.')
    parser.add_argument('-a','--album',dest='album',\
            type=str, default=None,\
            help='''Select one album to process.
            If not given, process all albums in the library.''')

    parser.add_argument('-v','--verbose',action='store_true',\
        default=True, help='Print some texts.')
    try:
        args = parser.parse_args()
    except:
        #parser.print_help()
        sys.exit(1)

    dbfile = os.path.abspath(args.dbfile)
    outdir = os.path.abspath(args.outdir)

    main(dbfile,outdir,args.album,args.verbose)

