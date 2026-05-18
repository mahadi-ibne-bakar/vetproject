## Scheduled Tasks
The following command should be run every 5 minutes in production:
    python manage.py send_reminders
On Render paid tier, add a Cron Job service with the command above.
On free tier, you can trigger it manually or use an external cron service
like cron-job.org to hit a protected endpoint.