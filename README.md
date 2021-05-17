# PerfectFit virtual coach backend prototype

This should become a working prototype that can handle the following scenario: 
* User sends a message in the NiceDay app with the intent to get the planning for the next week 
* In response the Virtual Coach sends back the weekly planning that should include: 
  - Hey {name}, where the name is retrieved from the database 
  - One planned event is to read through some psycho-education that comes from a ‘content’ file (that will later be controlled by Leiden)
  - A suggestion for physical exercises from algorithm (nice to have)

(optional):
- The virtual coach asks the user whether it can plan these activities.
- If affirmative, the virtual coach adds these activities to the in-app calendar of the user.

See [the preliminary design](https://whimsical.com/perfectfit-UtvRnxdP8P79humXTnjb9J)

And an example conversation:

<img src="https://user-images.githubusercontent.com/9945255/116060273-054fb080-a682-11eb-9fe4-d864305bf4d2.png" width="300" >

## Architecture design
Take a look at the design [here](docs/design.md).

## Setup using docker-compose
1. See `niceday-api/` for getting the therapist user id and token. 
2. Create a file called `.env` in the root of this app.
Save the therapist user id and token in your `.env` file as THERAPIST_USER_ID and NICEDAY_TOKEN respectively,
see .env-example. These will be loaded as environment variables and will thus be available in the app.
NB: The token expires, so you need to replace it once in a while. 
You will get a `ChatNotAuthorizedError` if the token is invalid.
3. Run `docker-compose --env-file .env up`