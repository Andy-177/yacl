import yacl
with open("config.ycl", "r", encoding="utf-8") as f:
    result = yacl.load(f)
print(result)