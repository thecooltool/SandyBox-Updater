'''
Documentation, License etc.

@package module
'''

import subprocess
import tempfile
import shutil
import urllib2
import sys
import os


tempPath = ''
scriptVersion = 1
rsaKey = '/home/alexander/machinekit/image/fat/ssh/id_rsa'
gitHubUrl = 'https://raw.githubusercontent.com/thecooltool/Sandy-Box-Updater/master/'


def createTempPath():
    global tempPath
    tempPath = tempfile.mkdtemp(prefix='sandy-box-updater')


def clearTempPath():
    shutil.rmtree(tempPath)
    

def exitScript(message):
    sys.stderr.write(message)
    sys.stderr.write('\n')
    
    if tempPath is not '':
        clearTempPath()
    
    sys.exit(1)


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
    
    remoteFile = gitHubUrl + 'version.txt'
    localFile = os.path.join(tempPath, 'version.txt')
    currentScript = os.path.realpath(__file__)
    scriptName = os.path.basename(currentScript)
    remoteScript = gitHubUrl + scriptName
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

def runSshCommand(command):
    lines = ''
    fullCommand = 'ssh -i ' + rsaKey + ' -oStrictHostKeyChecking=no -oUserKnownHostsFile=/dev/null machinekit@192.168.7.2' 
    fullCommand = fullCommand.split(' ')
    fullCommand.append(command)
    
    p = subprocess.Popen(fullCommand, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    while(True):
      retcode = p.poll() #returns None while subprocess is running
      lines += p.stdout.readline()
      if(retcode is not None):
        break
    
    return lines

def copyToHost(localFile, remoteFile):
    lines = ''
    fullCommand = 'scp -i ' + rsaKey + ' -oStrictHostKeyChecking=no -oUserKnownHostsFile=/dev/null' 
    fullCommand = fullCommand.split(' ')
    fullCommand.append(localFile)
    fullCommand.append('machinekit@192.168.7.2:' + remoteFile)
    
    sys.stdout.write("Copying " + os.path.basename(localFile) + " to remote host ...")
    p = subprocess.Popen(fullCommand, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    while(True):
      retcode = p.poll() #returns None while subprocess is running
      if(retcode is not None):
        break
    
    sys.stdout.write("done\n")
    return retcode

def installPackage(package, name):
    remotePackage = gitHubUrl + 'packages/' + package
    localPackage = os.path.join(tempPath, package)
    hostPackage = '~/' + package
    
    output = runSshCommand('source /etc/profile; dpkg-query -l ' + name + ' || echo not_installed')
    if 'not_installed' in output:
        downloadFile(remotePackage, localPackage)
        copyToHost(localPackage, hostPackage)
        sys.stdout.write('Intalling package ' + package + '...')
        output = runSshCommand('source /etc/profile; sudo dpkg -i ' + hostPackage + ' || echo error')
        if 'error' in output:
            exitScript('installing package ' + package + ' failed')
        sys.stdout.write('done\n')

def main():
    createTempPath()
    
    lines = runSshCommand('source /etc/profile; dpkg-query -l apt-offline || echo not_installed')
    if 'not_installed' in lines:
        print('oh noez')
    
    installPackage('apt-offline_1.2_all.deb', 'apt-offline')
    
    clearTempPath()
