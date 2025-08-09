from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date
import getpass
import tkinter as tk
import sys
import os
import paramiko
import time
import configparser
import shutil
import zipfile
import json
import gspread

class DatetimeEncoder(json.JSONEncoder):
    def default(self, obj):
        try:
            return super(DatetimeEncoder, obj).default(obj)
        except TypeError:
            return str(obj)

def next_available_row3(wks5):
    str_list9 = list(filter(None, wks5.col_values(2)))
    return str(len(str_list9) + 1)


scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

json_key = r'''
{

}
'''

try:
    json_data = json.loads(json_key)
    
    credentials2 = ServiceAccountCredentials.from_json_keyfile_dict(json_data, scope)
    gc2 = gspread.authorize(x)
    wks5 = gc2.open("takpakauth").worksheet("x")
    val0 = wks5.cell(2, 6).value
    if val0 != "1":
        next_row = next_available_row3(wks5)
        current_datetime = datetime.now()
        formatted_datetime = current_datetime.strftime("%A, %m/%d/%Y %I:%M:%S %p")
        wks5.update_acell("B{}".format(next_row), getpass.getuser())
        wks5.update_acell("C{}".format(next_row), formatted_datetime)
        wks5.update_acell("D{}".format(next_row), "x")
        sys.exit()

    next_row = next_available_row3(wks5)
    
    current_datetime = datetime.now()
    formatted_datetime = current_datetime.strftime("%A, %m/%d/%Y %I:%M:%S %p")

    wks5.update_acell("B{}".format(next_row), getpass.getuser())
    wks5.update_acell("C{}".format(next_row), formatted_datetime)
    wks5.update_acell("D{}".format(next_row), "TAKPAK")
except (gspread.exceptions.GSpreadException, Exception):  
    print("Unable to connect")
    sys.exit()  


class GUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("TAKPAK")
        self.root.attributes("-alpha", 0.7)
        self.filename_entry = tk.Entry(self.root)
        self.filename_entry.pack()
        self.submit_button = tk.Button(self.root, text="Create", command=self.submit)
        self.submit_button.pack()
        self.submit_button = tk.Button(self.root, text="Pack", command=self.pack)
        self.submit_button.pack()
        self.restart_svr_button = tk.Button(self.root, text="Restart SVR", command=self.restart_svr)
        self.restart_svr_button.pack()
        self.textbox = tk.Text(self.root, bg='#242424', fg='white')
        self.textbox.pack()
        self.stdout = StdoutRedirector(self.textbox)
        sys.stdout = self.stdout
        self.root.mainloop()

    def pack(self):
        print("packing")

        takserver_file = None
        if os.path.exists(os.path.join('package', 'takserver.p12')):
            takserver_file = os.path.join('package', 'takserver.p12')

        output_dir = 'output'
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open('package/secure.txt', 'r') as infile:
            secure_contents = infile.read()

        for filename in os.listdir('input'):
            if filename.endswith('.p12'):
                value = filename[:-4]

                ios_package_dir = os.path.join(output_dir, value + ".TAK.Server.Package")
                source_file = os.path.join('input', filename)
                os.makedirs(ios_package_dir, exist_ok=True)

                with open(os.path.join(ios_package_dir, 'secure.pref'), 'w') as outfile:
                    outfile.write(secure_contents.replace('CHANGE', value))
                shutil.copy(source_file, os.path.join(ios_package_dir, value + '.p12'))

                if takserver_file:
                    shutil.copy(takserver_file, os.path.join(ios_package_dir, 'takserver.p12'))

                with zipfile.ZipFile(os.path.join(output_dir, value + 'iOS.zip'), 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for root, dirs, files in os.walk(ios_package_dir):
                        for file in files:
                            zip_file.write(os.path.join(root, file), file)
                shutil.rmtree(ios_package_dir)
                android_package_dir = os.path.join(output_dir, value + ".TAK.Android.Package")
                os.makedirs(android_package_dir, exist_ok=True)
                dest_file = os.path.join(android_package_dir, value + '.p12')
                shutil.copy(source_file, dest_file)

                source_dir = 'androidPackage'
                if not os.path.exists(source_dir):
                    print("No Android package directory found. Skipping...")
                    continue

                for root, dirs, files in os.walk(source_dir):
                    for file in files:
                        if file == 'manifest.xml':
                            manifest_dir = os.path.join(android_package_dir, 'MANIFEST')
                            os.makedirs(manifest_dir, exist_ok=True)
                            shutil.copy(os.path.join(root, file), os.path.join(manifest_dir, file))

                            with open(os.path.join(manifest_dir, file), 'r') as manifest:
                                manifest_contents = manifest.read()
                            with open(os.path.join(manifest_dir, file), 'w') as manifest:
                                manifest.write(manifest_contents.replace('CHANGE', value))
                        elif file != 'secure.txt':
                            shutil.copy(os.path.join(root, file), android_package_dir)

                with open(os.path.join(android_package_dir, 'secure.pref'), 'w') as outfile:
                    outfile.write(open(os.path.join(source_dir, 'secure.txt'), 'r').read().replace('CHANGE', value))

                if takserver_file:
                    shutil.copy(takserver_file, os.path.join(android_package_dir, 'takserver.p12'))

                with zipfile.ZipFile(os.path.join(output_dir, value + '_android.zip'), 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for root, dirs, files in os.walk(android_package_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            zip_file.write(file_path, os.path.join(os.path.relpath(root, android_package_dir), file))

                shutil.rmtree(android_package_dir)
                print("packed")

    def restart_svr(self):
        print("Restarting SVR...")

        config = configparser.ConfigParser()
        config.read('config.ini')
        address = config.get('Server', 'address')
        username = config.get('Server', 'username')
        password = config.get('Server', 'password')
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(address, username=username, password=password)

        restart_command = f"echo 'x' | sudo -S systemctl restart takserver"

        try:
            stdin, stdout, stderr = ssh.exec_command(restart_command)
            for line in stdout:
                print(line.strip())
            for line in stderr:
                print(line.strip())
            print("Restarted SVR")
        except Exception as e:
            print(f"Error in restarting SVR: {e}")
        finally:
            ssh.close()      
        
    def submit(self):
        filename = self.filename_entry.get()
        main(filename, self.textbox)

class StdoutRedirector:
    def __init__(self, textbox):
        self.textbox = textbox

    def write(self, message):
        self.textbox.insert(tk.END, message)




def main(filename, textbox):
    config = configparser.ConfigParser()
    config.read('config.ini')
    address = config.get('Server', 'address')
    username = config.get('Server', 'username')
    password = config.get('Server', 'password')
    restart_server = config.getint('Server', 'restart_server')
    default_group = config.get('Server', 'DefaultGroup') 

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(address, username=username, password=password)

    sudo_password = password
    commands = f"echo 'x' | sudo -S su tak && cd /opt/tak/certs && ./makeCert.sh client {filename}"

    try:
        stdin, stdout, stderr = ssh.exec_command(commands)
        for line in stdout:
            print(line.strip())
        for line in stderr:
            print(line.strip())
        print("User: TAK")
        time.sleep(1)
        textbox.see(tk.END)
        textbox.update()
        stdin, stdout, stderr = ssh.exec_command("exit")
        time.sleep(3)
        textbox.see(tk.END)
        textbox.update()
        commands = [
            f"echo 'x' | sudo -S su",
            f"cd /opt/tak/utils", 
            f"java -jar UserManager.jar certmod -g Offsite /opt/tak/certs/files/{filename}.pem" 
        ]

        command_string = " && ".join(commands)

        stdin, stdout, stderr = ssh.exec_command(command_string)
        output = stdout.read().decode('utf-8')
        errors = stderr.read().decode('utf-8')

        print("Output:", output)
        print("Errors:", errors)

        time.sleep(4)
        textbox.see(tk.END)
        textbox.update()
    except Exception as e:
        print(f"Error executing command: {e}")
    print("Commands executed successfully.")

    if not os.path.exists('input'):
        os.makedirs('input')

    remote_path = f"/opt/tak/certs/files/{filename}.p12"
    local_path = os.path.join(os.getcwd(), 'input', f"{filename}.p12") 
    print(f"Copying file from {remote_path} to {local_path}...")
    try:
        sftp = ssh.open_sftp()
        sftp.get(remote_path, local_path)
        sftp.close()
        print("File copied successfully.")
    except Exception as e:
        print(f"Error: {e}")
    ssh.close()


if __name__ == "__main__":
    gui = GUI()








