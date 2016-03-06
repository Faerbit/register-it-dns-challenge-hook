#register.it DNS Challenge hook

This scripts is a hook for the dns-01 challenge from the ACME Protocol for
domains registered with [register.it](https://register.it).

##Dependencies
This scripts depends on **Python 3**, and the python packages listed in the
`requirements.txt`. This also needs **phantomjs**.

##Configuration
Copy the example.ini to default.ini and fill in the necessary details.

##Usage
Run the script as a hook with your favourite ACME client. The CLI is as
follows:
The script supports the modes `deploy_challenge` and `clean_challenge`.  These
strings have to be the first parameter. The second parameter is the domain to
which the TXT record should be attached. The last parameter is the value for
the TXT record(only when deploying the challenge)

Example:
```
./hook.py deploy_challenge _acme-challenge.domain.it SECRET-VALUE
```

##License
This code is licensed under the MIT License. See LICENSE.md for more details.
