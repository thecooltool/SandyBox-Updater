'''
Documentation, License etc.

@package module
'''

import tempfile
import shutil
import urllib2
import sys
import os


tempPath = ''
scriptVersion = 1


def createTempPath():
    global tempPath
    tempPath = tempfile.mkdtemp(prefix='sandy-box-updater')


def clearTempPath():
    shutil.rmtree(tempPath)


def formatSize(num, suffix='B'):
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def downloadFile(url, filePath):
    request = urllib2.Request(url)
    request.add_header('User-Agent', 'Mozilla/5.0') # Spoof request to prevent caching
    request.add_header('Pragma', 'no-cache')
    u = urllib2.build_opener().open(request)
    f = open(filePath, 'wb')
    meta = u.info()
    fileSize = int(meta.getheaders("Content-Length")[0])
    fileSizeStr = formatSize(fileSize)
    print("Downloading: {0}".format(url.split('/')[-1]))

    fileSizeDl = 0
    blockSize = 8192
    while True:
        buffer = u.read(blockSize)
        if not buffer:
            break

        fileSizeDl += len(buffer)
        fileSizeDlStr = formatSize(fileSizeDl)
        f.write(buffer)
        p = float(fileSizeDl) / fileSize
        status = r"{0}/{1}  [{2:.3%}]".format(fileSizeDlStr, fileSizeStr, p)
        status = status + chr(8)*(len(status)+1)
        sys.stdout.write(status)

    sys.stdout.write('\n')
    f.close()


def updateScript():
    createTempPath()
    
    remoteFile = 'https://raw.githubusercontent.com/thecooltool/Sandy-Box-Updater/master/version.txt'
    localFile = os.path.join(tempPath, 'version.txt')
    currentScript = os.path.realpath(__file__)
    scriptName = os.path.basename(currentScript)
    remoteScript = 'https://raw.githubusercontent.com/thecooltool/Sandy-Box-Updater/master/' + scriptName
    localScript = os.path.join(tempPath, scriptName)

    downloadFile(remoteFile, localFile)

    remoteVersion = 0
    with open(localFile, 'r') as f:
        remoteVersion = int(f.readline())

    updated = False
    if remoteVersion > scriptVersion:
        print('Updating update script')
        downloadFile(remoteScript, localScript)
        shutil.copyfile(localScript, currentScript)
        update = True
    
    clearTempPath()
    return updated


def main():
    createTempPath()
    print('version: ' + str(scriptVersion))
    clearTempPath()
