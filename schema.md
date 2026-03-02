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

    "role": "user",
    "status": "active",

    "created_at": ISODate("..."),
    "last_login_at": ISODate("...")
}
```