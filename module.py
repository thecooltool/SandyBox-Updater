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
import json
import urlparse
import httplib

tempPath = ''
scriptVersion = 1
rsaKey = '/home/alexander/machinekit/image/fat/ssh/id_rsa'
gitHubUrl = 'https://raw.githubusercontent.com/thecooltool/Sandy-Box-Updater/master/'
aptOfflineExec = '/home/alexander/bin/apt-offline/apt-offline'


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


# Recursively follow redirects until there isn't a location header
def resolveHttpRedirect(url, depth=0):
    if depth > 10:
        raise Exception("Redirected "+depth+" times, giving up.")
    o = urlparse.urlparse(url,allow_fragments=True)
    conn = httplib.HTTPConnection(o.netloc)
    path = o.path
    if o.query:
        path +='?'+o.query
    conn.request("HEAD", path)
    res = conn.getresponse()
    headers = dict(res.getheaders())
    if headers.has_key('location') and headers['location'] != url:
        return resolveHttpRedirect(headers['location'], depth+1)
    else:
        return url
    
    
def downloadFile(url, filePath):
    request = urllib2.Request(resolveHttpRedirect(url))
    request.add_header('User-Agent', 'Mozilla/5.0') # Spoof request to prevent caching
    request.add_header('Pragma', 'no-cache')
    u = urllib2.build_opener().open(request)
    meta = u.info()
    fileSize = int(meta.getheaders("Content-Length")[0])
    fileSizeStr = formatSize(fileSize)
    print("Downloading: {0}".format(url.split('/')[-1]))

    f = open(filePath, 'wb')
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
    
    sys.stdout.write(" done\n")
    return retcode

def copyFromHost(remoteFile, localFile):
    lines = ''
    fullCommand = 'scp -i ' + rsaKey + ' -oStrictHostKeyChecking=no -oUserKnownHostsFile=/dev/null' 
    fullCommand = fullCommand.split(' ')
    fullCommand.append('machinekit@192.168.7.2:' + remoteFile)
    fullCommand.append(localFile)
    
    sys.stdout.write("Copying " + os.path.basename(localFile) + " from remote host ...")
    p = subprocess.Popen(fullCommand, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    while(True):
      retcode = p.poll() #returns None while subprocess is running
      if(retcode is not None):
        break
    
    sys.stdout.write(" done\n")
    return retcode


def checkHostPath(remotePath):
    output = runSshCommand('ls ' + remotePath + ' || echo doesnotexist')
    return not ('doesnotexist' in output)


def removeHostPath(remotePath):
    output = runSshCommand('rm -r -f ' + remotePath + ' || echo removefailed')
    return not ('removefailed' in output)


def moveHostPath(src, dst):
    output = runSshCommand('mv ' + src + ' ' + dst + ' || echo removefailed')
    return not ('removefailed' in output)


def makeHostPath(remotePath):
    output = runSshCommand('mkdir -p ' + remotePath + ' || echo mkdirfailed')
    return not ('mkdirfailed' in output)


def unzipOnHost(zipFile, remotePath):
    sys.stdout.write('unzipping ' + os.path.basename(remotePath) + ' ... ')
    output = runSshCommand('unzip ' + zipFile + ' -d ' + remotePath + ' || echo unzipfailed')
    if 'unzipfailed' in output:
        sys.stdout.write(' failed\n')
        return False
    else:
        sys.stdout.write(' done\n')
        return True


def checkPackage(name):
    sys.stdout.write('checking for package ' + name + ' ... ')
    output = runSshCommand('source /etc/profile; dpkg-query -l ' + name + ' || echo not_installed')
    if 'not_installed' in output:
        sys.stdout.write('not installed\n')
        return False
    else:
        sys.stdout.write('installed\n')
        return True


def installPackage(package, name):
    remotePackage = gitHubUrl + 'packages/' + package
    localPackage = os.path.join(tempPath, package)
    hostPackage = '~/' + package
    
    if not checkPackage(name):
        
        downloadFile(remotePackage, localPackage)
        copyToHost(localPackage, hostPackage)
        sys.stdout.write('Intalling package ' + package + ' ... ')
        output = runSshCommand('source /etc/profile; sudo dpkg -i ' + hostPackage + ' || echo installerror')
        if 'installerror' in output:
            exitScript('installing package ' + package + ' failed')
        sys.stdout.write('done\n')


def aptOfflineBase(command):
    sigName = 'apt-offline.sig'
    localSig = os.path.join(tempPath, sigName)
    hostSig = '/tmp/' + sigName
    bundleName = 'bundle.zip'
    localBundle = os.path.join(tempPath, bundleName)
    hostBundle = '/tmp/' + bundleName
    
    sys.stdout.write('updating repositories ...')
    output = runSshCommand('sudo apt-offline set ' + command + ' ' + hostSig + ' || echo updateerror')
    if 'updateerror' in output:
        exitScript(' failed')
    else:
        sys.stdout.write(' done\n')
    
    if copyFromHost(hostSig, localSig) != 0:
        exitScript('copy failed')
        
    if os.path.isfile(localBundle):
        os.remove(localBundle)
        
    command = aptOfflineExec + ' get --threads 4 --bundle ' + localBundle + ' ' + localSig
    command = command.split(' ')
    sys.stdout.write('local update ...')
    p = subprocess.Popen(command)
    while(True):
      retcode = p.poll() #returns None while subprocess is running
      if(retcode is not None):
        break
    
    if retcode != 0:
        exitScript(' failed\n')
    else:
        sys.stdout.write(' done\n')
        
    if copyToHost(localBundle, hostBundle) != 0:
        exitScript('copy failed')
        
    sys.stdout.write('installing repository update ... ')
    output = runSshCommand('sudo apt-offline install ' + hostBundle + ' || echo installerror')
    if 'installerror' in output:
        exitScript(' failed')
    else:
        sys.stdout.write(' done\n')


def aptOfflineUpdate():
    aptOfflineBase('--update --upgrade')
    sys.stdout.write('upgrading packages ... ')
    output = runSshCommand('sudo apt-get upgrade -y || echo installerror')
    if 'installerror' in output:
        exitScript(' failed\n')
    else:
        sys.stdout.write(' done\n')
        
def aptOfflineInstallPackages(names):
    namesList = names.split(' ')
    necessary = False
    for name in namesList:
        if not checkPackage(name):
            necessary = True
            break
        
    if not necessary:
        return 
    
    aptOfflineBase('--install-packages ' + names + ' --update')
    sys.stdout.write('installing packages ... ')
    output = runSshCommand('sudo apt-get install -y ' + names + ' || echo installerror')
    if 'installerror' in output:
        exitScript(' failed\n')
    else:
        sys.stdout.write(' done\n')
    

def compareGitRepo(user, repo, path):
    url = 'https://api.github.com/repos/' + user + '/' + repo + '/git/refs/heads/master'
    
    request = urllib2.Request(url)
    request.add_header('User-Agent', 'Mozilla/5.0') # Spoof request to prevent caching
    request.add_header('Pragma', 'no-cache')
    u = urllib2.build_opener().open(request)
    
    data = '' 
    blockSize = 8192
    while True:
        buffer = u.read(blockSize)
        if not buffer:
            break
        
        data += buffer
        
    repoObject = json.loads(data)
    remoteSha = repoObject['object']['sha']
    
    done = True
    output = runSshCommand('cd ' + path + ';git rev-parse HEAD || echo parseerror')
    if 'parseerror' in output:
        done = False
        
    if not done:    # remote is not git repo, try to read sha file
        shaFile = os.path.join(path, 'git-sha')
        output = runSshCommand('cat ' + shaFile + ' || echo parseerror')
        if 'parseerror' in output:
            return False
        
    hostSha = output.split('\n')[-2]   # sha is on the semi-last line
    
    return remoteSha == hostSha


def downloadGitRepo(user, repo, path):
    url = 'https://github.com/' + user + '/' + repo + '/archive/master.zip'
    downloadFile(url, path)

def updateGitRepo(user, repo, path, commands):
    necessary = False
    fileName = repo + '.zip'
    localFile = os.path.join(tempPath, fileName)
    hostFile = '/tmp/' + fileName
    shaFile = os.path.join(path, 'git-sha')
    
    sys.stdout.write('checking if git repo ' + repo + ' is up to date ... ')
    if not checkHostPath(path):
        necessary = True
        
    if not necessary:
        necessary = not compareGitRepo(user, repo, path)
        
    if necessary:
        sys.stdout.write(' not\n')
        
        if not removeHostPath(path):
            exitScript('removing path failed')
        
        downloadGitRepo(user, repo, localFile)
        
        if copyToHost(localFile, hostFile) != 0:
            exitScript('copy failed')
        
        if not unzipOnHost(hostFile, path + '-tmp'):
            exitScript('unzip failed')
            
        if not moveHostPath(path + '-tmp/' + repo + '-master', path):
            exitScript('move failed')
            
        if not removeHostPath(path + '-tmp'):
            exitScript('remove failed')
            
        output = runSshCommand('unzip -z ' + hostFile + ' >> ' + shaFile  + ' || echo commanderror')
        if 'commanderror' in output:
            exitScript('sha dump failed')
            
        for command in commands:
            sys.stdout.write('executing ' + command + ' ... ')
            output = runSshCommand('source /etc/profile; cd ' + path + '; ' + command + ' || echo commanderror')
            if 'commanderror' in output:
                exitScript(' failed')
            else:
                sys.stdout.write(' done\n')
        
    else:
        sys.stdout.write(' yes\n')
    
def main():
    createTempPath()
    
    #installPackage('apt-offline_1.2_all.deb', 'apt-offline')
    #aptOfflineUpdate()
    #aptOfflineInstallPackages('machinekit-dev')
    #aptOfflineInstallPackages('zip unzip')
    
    updateGitRepo('strahlex', 'AP-Hotspot', '~/bin/AP-Hotspot', ['sudo make install'])
    #updateGitRepo('strahlex', 'mjpeg-streamer', '~/bin/mjpeg-streamer', [])
    updateGitRepo('thecooltool', 'machinekit-configs', '~/machinekit-configs', [])
    updateGitRepo('thecooltool', 'example-gcode', '~/nc_files/examples', [])
    
    if not makeHostPath('~/nc_files/share'):
        exitScript('failed to create directory')
    
    clearTempPath()
