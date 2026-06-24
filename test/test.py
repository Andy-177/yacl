import yacl
with open("test.ycl", "r", encoding="utf-8") as f:
    result = yacl.load(f)
print(result)