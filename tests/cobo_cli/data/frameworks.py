from enum import Enum, unique


@unique
class FrameworkEnum(Enum):
    fastapi = "fastapi"
    nextjs = "nextjs"


FrameworkEnum.fastapi.repo = (
    "https://d.cobo.com/public/documents/portal-helloworld-python-fastapi.zip"
)
FrameworkEnum.nextjs.repo = (
    "https://d.cobo.com/public/documents/portal-helloworld-js-nextjs.zip"
)

FrameworkEnum.fastapi.run_command = "fastapi run main.py"
FrameworkEnum.nextjs.run_command = "pnpm dev"
