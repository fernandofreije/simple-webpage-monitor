# Simple Web Page Monitor
Just a very simple webpage monitor that notifies you on changes.


## SETUP

### Example config/pages.yml file

```yaml
"put here the name of the page":
  url: the url of the page
  selector: an xpath selector
  refresh_time: number of seconds you want to wait between check and check
"put here the name of the page":
  url: the url of the page
  selector: an xpath selector
  refresh_time: number of seconds you want to wait between check and check

```

### Example config/config.yml file

```yaml
#webhook_url: Put here your webhook url
#driver_path: Put here the selenium driver path
log_level: INFO

```