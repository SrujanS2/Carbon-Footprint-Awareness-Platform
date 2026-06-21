import kagglehub

# Download latest version
path = kagglehub.dataset_download("sonalshinde123/personal-carbon-footprint-behavior-dataset")

print("Path to dataset files:", path)