[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=PerfectFit-project_rasa-bot&metric=alert_status)](https://sonarcloud.io/dashboard?id=PerfectFit-project_rasa-bot)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=PerfectFit-project_rasa-botr&metric=coverage)](https://sonarcloud.io/dashboard?id=PerfectFit-project_rasa-bot)

# PerfectFit virtual coach server functional prototype
This should become a working functional prototype that can handle the following scenario. It is a functional system that facilitates a subset of the must have requirements, that can easily be extended with specific content to match the patient journey. It is not yet production ready.

* User sends a message in the NiceDay app with the intent to get the planning for the next week
* In response the Virtual Coach sends back the weekly planning that should include:
  - Hey {name}, where the name is retrieved from the database
  - One planned event is to read through some psycho-education that comes from a ‘content’ file (that will later be controlled by Leiden)
  - A suggestion for physical exercises from algorithm (nice to have)

(optional):
- The virtual coach asks the user whether it can plan these activities.
- If affirmative, the virtual coach adds these activities to the in-app calendar of the user.

And an example conversation:

<img src="https://user-images.githubusercontent.com/9945255/116060273-054fb080-a682-11eb-9fe4-d864305bf4d2.png" width="300" >

## Software development planning
See [software development planning document](https://nlesc.sharepoint.com/:w:/r/sites/team-flow/Shared%20Documents/PerfectFit/Perfect%20Fit%20-%20RFCs/PerfectFit-RFC-0007-software-development-planning.docx?d=w434661cbf10c458998e9e45ea6451ea4&csf=1&web=1&e=8cxoLW)

## Architecture design
Take a look at the design [here](docs/design.md).

## Setup using docker-compose
1. Create a file called `.env` in the root of this app.
Save the therapist user id and password in your `.env` file as THERAPIST_USER_ID and THERAPIST_PASSWORD, respectively,
see .env-example. Note that no token needs to be created and specificied, as we now get the token automatically in the niceday-api and niceday-broker based on the credentials.
2. Make sure you have access to the goalie-js repository from SenseHealth.
3. Run `./script/server`. This will install the right dependencies, build docker images, and
run them. If you get an error with regards to Docker on Windows, run `docker-compose up --build --force-recreate` from script/server yourself.

## Setting up an account in the NiceDay alpha app
1. Download the NiceDay alpha version on your phone. 
2. Open the downloaded app and create a client account. This can be with the same credentials as for the normal NiceDay app.
3. Login to the downloaded app on your phone with the account you just created.
4. Send a connection request to the "PerfectFitTherapist Test"-therapist from the app.
5. Login to the therapist account on https://alpha.niceday.app/ and accept the connection request from the client.
