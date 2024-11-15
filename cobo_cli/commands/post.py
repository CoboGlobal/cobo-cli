from cobo_cli.utils.api import create_api_command

post_api = create_api_command("post")
post_api.help = "Make a POST request to a Cobo API endpoint."

if __name__ == "__main__":
    post_api()
