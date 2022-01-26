# Guidelines for pushing to heroku
# Make sure heroku cli is installed
# Login to heroku
heroku login

# Make sure the right remote is configured
heroku git:remote -a perfectfit-rasa-server

# Login to container registry
heroku container:login

# Push web app
heroku container:push:web

# Deploy changes
heroku container:release web
