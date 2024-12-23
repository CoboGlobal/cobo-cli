from cobo_cli.utils.api import create_api_command

put_api = create_api_command("put")
put_api.help = "Make a PUT request to a Cobo API endpoint."

if __name__ == "__main__":
    put_api()
