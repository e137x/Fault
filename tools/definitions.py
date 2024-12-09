import pymongo

cluster = pymongo.MongoClient("mongodb+srv://esjjo:cerealgotyou@esjjo.ysu1c.mongodb.net/?retryWrites=true&w=majority&appName=Esjjo")
db = cluster["Fault"]



async def get_default_autoplay(guild_id):
    collection = db["Autoplays"]
    find = collection.find_one(
        {
            "id": guild_id
        }
    )
    if find:
        return find["autoplay"]
    else:
        return None
    

async def get_default_volume(guild_id):
    collection = db["Volumes"]
    find = collection.find_one(
        {
            "id": guild_id
        }
    )
    if find:
        return find["volume"]
    else:
        return 100
    

async def get_guild_247(guild_id):
    collection = db["24/7"]
    find = collection.find_one(
        {
            "id": guild_id
        }
    )
    if find:
        return find["24/7"]
    else:
        return None