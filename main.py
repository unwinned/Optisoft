import asyncio
import sys
from utils.router import Router
import colorama
import pyfiglet
from cryptography.fernet import Fernet
from termcolor import colored
from colorama import Fore

def zalupa(cipher, string):
    return cipher.decrypt(string).decode()

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def run():
    router = Router(__file__)
    colorama.init()
    rkkt1 = pyfiglet.figlet_format("DEVS:")
    print(Fore.CYAN + rkkt1)
    gentle = "Specially made for Gentleman's Chronicles: https://t.me/GentleChron \n"
    unwinned = "unwinned: https://t.me/unwinnedcrypto \n"
    # time.sleep(2)
    version = 'Optisoft\nCurrent version: v1'
    devs_c = colored(text=gentle + unwinned, color="red", attrs=["bold"])
    version_c = colored(text=version, color="red", attrs=["bold"])
    print(devs_c)
    # time.sleep(2)
    print(version_c + "\n")
    # time.sleep(1)
    await router.route()
    
if __name__ == "__main__":
    asyncio.run(run())
