import requests
response = requests.get('https://fakestoreapi.com/products')
print(response.json())