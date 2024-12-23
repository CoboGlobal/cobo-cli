from cobo_cli.utils.api import create_api_command

delete_api = create_api_command("delete")
delete_api.help = "Make a DELETE request to a Cobo API endpoint."

if __name__ == "__main__":
    delete_api()
