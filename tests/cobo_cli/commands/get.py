from cobo_cli.utils.api import create_api_command

get_api = create_api_command("get")
get_api.help = "Make a GET request to a Cobo API endpoint."

if __name__ == "__main__":
    get_api()
