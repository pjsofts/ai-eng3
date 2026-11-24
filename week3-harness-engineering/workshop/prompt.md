please create three systems on different ports

one of them is a simulation of an ecommerce website
we don't actually want the website 
but we want a health route
which we can curl and get status of the system in a json
if it's running or it has a problem


one system is the operator dashboard
dashboard has a place which shows different system events
also shows the health of the ecomerce website 
also has an inbox for the operator to see messages and answer them
please implement ui using react


one of them is a backgroud agents
this agents wakes up when there is a new event
when there is an event the agent gets the health of the system from the ecommerce website
it tries to fix the problem 
or send messages to inbox in operator dashbord for confirmation
or asks for help

also we want to have some drills to show that our agent is working well or not
we can run different drills:

1. feature fault ->  when we trigger this drill the ecommerce website returns unhealthy status with details of feature fault and our agent investigates the logs and then triggers disable feature on the ecommerce website and then the staus becomes health, each step we can see the events and the steps of our agent run time

2. bad release -> when we trigger this drill the release should be roll backed and then the system becomes healthy
here our agent asks for confimation from the inbox

3. depdency problem ->  the ecommerce platform becomes unhealthy and our background agent can't fix it, and then it automatically heals after 30 seconds, and then event is passed to our background agent and it continues its work

4. dependencey problem-> here our background agent can't do anything and ask for help in the inbox