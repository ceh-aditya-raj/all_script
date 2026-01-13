import subprocess
import zipfile
from ftplib import FTP

# -----------------------------
# CONFIGURATION
# -----------------------------
ip = "localhost"
ports = [21, 22, 25, 80, 443]
port_str = ",".join(map(str, ports))

scan_file = "nmap.txt"
hash_file = "hash.txt"
zip_file = "submission.zip"

ftp_server = "ftp.example.com"
ftp_user = "username"
ftp_pass = "password"

# -----------------------------
# STEP 1: NMAP SCAN
# -----------------------------
print("[+] Starting Nmap scan...")

subprocess.run(
    [
        "nmap",
        "-A",
        "-p", port_str,
        "-sC",
        "-sV",
        "-oN", scan_file,
        ip
    ],
    capture_output=True,
    text=True
)

print("[+] Nmap scan completed")

# -----------------------------
# STEP 2: HASH GENERATION
# -----------------------------
print("[+] Generating SHA256 hash...")

hash_result = subprocess.run(
    ["sha256sum", scan_file],
    capture_output=True,
    text=True
)

with open(hash_file, "w") as f:
    f.write(hash_result.stdout)

print("[+] Hash generated")

# -----------------------------
# STEP 3: ZIP CREATION
# -----------------------------
print("[+] Creating ZIP file...")

with zipfile.ZipFile(zip_file, "w") as zipf:
    zipf.write(scan_file)
    zipf.write(hash_file)

print("[+] ZIP file created")

# -----------------------------
# STEP 4: FTP UPLOAD
# -----------------------------
print("[+] Uploading files to FTP server...")

ftp = FTP(ftp_server)
ftp.login(ftp_user, ftp_pass)

with open(zip_file, "rb") as f:
    ftp.storbinary(f"STOR {zip_file}", f)

with open(hash_file, "rb") as f:
    ftp.storbinary(f"STOR {hash_file}", f)

ftp.quit()

print("[+] FTP upload completed successfully")
