# Database Schema

## users

Collection: users

```
users:
{
    "_id": ObjectId("..."),
    "full_name": "Jane Doe",
    "netid": "jd1234",
    "email": "jane.doe@nyu.edu",
    "password_hash": "pbkdf2:sha256:...",

    "role": "user", // "user" or "admin"
    "status": "active", // "active", "suspended", "deactivated"

    "created_at": ISODate("..."),
    "last_login_at": ISODate("...")
}
```

# posts

Collection: posts

```
posts:
{
    "_id": ObjectId("..."),

    "title": "Black North Face Backpack",
    "description": "Lost near Bobst library around 3pm. Contains a laptop and notebooks.",

    "type": "lost", // "lost" or "found"
    "status": "open", // "open", "resolved", "claimed"

    "location_text": "Bobst Library",
    "date_lost_or_found": ISODate("..."),

    "created_by": ObjectId("..."), // reference to users._id
    "created_at": ISODate("..."),

    "updated_at": ISODate("...")
}
```