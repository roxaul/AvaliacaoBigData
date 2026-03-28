import kagglehub

# Download latest version
path = kagglehub.dataset_download("waddahali/top-1000-steam-games-20242026")

print("Path to dataset files:", path)