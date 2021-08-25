// Login to niceday server and print user ID and Token
// Run this script with `node login.mjs emailaddress password`
import { Authentication, SenseServer } from '@sense-os/goalie-js';
import 'isomorphic-fetch'


const authSdk = new Authentication(SenseServer.Alpha);

// Read in command line arguments
var args = process.argv.slice(2)
var emailAddress = args[0]
var password = args[1]

authSdk.login(emailAddress, password).then(response => {
    console.log('THERAPIST_USER_ID=', response.user.id, '\nNICEDAY_TOKEN=', response.token);
});
