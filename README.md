# ansible-kong-module
A Module to help manage a [Kong](http://getkong.com) API Gateway

> For a full write-up, please see the blog series: [Kong Up and Running](http://blog.toast38coza.me/kong-up-and-running/)

**Requirements**

* Ansible
* python requests library
* Docker and Docker Compose

**Quickstart**


From a Docker-enabled terminal run:

```
git clone git@github.com:toast38coza/ansible-kong-module.git && cd ansible-kong-module
docker-compose up
```

This might take a while to run ... after it is finished you can find the IP of your docker machine with:

```
$ docker-machine ip default
> 1.2.3.4
```
(assuming your docker-machine is called default). 

You can then access your Kong API at: 

* **Admin interface:** 1.2.3.4:8001 
* **REST Interface:** 1.2.3.4:8000 


**Configure your Kong instance with:**

```
ansible-playbook playbook.yml -i inventory --extra-vars "kong_admin_base_url=1.2.3.4:8001 kong_base_url=1.2.3.4:8000"
```

* set kong_admin_base_url and kong_base_url to your Kong instance's urls