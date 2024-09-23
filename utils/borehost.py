import subprocess

server_proc = subprocess.Popen("bore-server_windows_amd64")

while True:
    tunnel_proc = subprocess.Popen("bore -s bore.digital -id liventcord -ls localhost -lp 80")

