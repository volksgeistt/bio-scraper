import discord
import asyncio
import re
import sys
import os
from datetime import datetime
from colorama import Fore, Back, Style, init
import pyfiglet

init(autoreset=True)

class Scraper:
    def __init__(self, token):
        self.client = discord.Client()
        self.token = token
        self.links = set()
        self.filename = f"links_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        
    def show_banner(self):
        banner = pyfiglet.figlet_format("Scraper", font="slant")
        print(Fore.RED + Style.BRIGHT + banner)
        print(Fore.WHITE + Style.BRIGHT + "- github.com/volksgeistt\n")
        print(Fore.YELLOW + "-" * 30)
        
    def log_info(self, message):
        print(Fore.BLUE + Style.BRIGHT + "[INFO] " + Style.RESET_ALL + message)
        
    def log_success(self, message):
        print(Fore.GREEN + Style.BRIGHT + "[SUCCESS] " + Style.RESET_ALL + message)
        
    def log_warning(self, message):
        print(Fore.YELLOW + Style.BRIGHT + "[WARNING] " + Style.RESET_ALL + message)
        
    def log_error(self, message):
        print(Fore.RED + Style.BRIGHT + "[ERROR] " + Style.RESET_ALL + message)
        
    def log_progress(self, current, total, member_name, link=None):
        progress = f"[{current}/{total}]"
        if link:
            print(Fore.GREEN + Style.BRIGHT + progress + Fore.WHITE + f" [ + ] Found link from " + 
                  Fore.CYAN + member_name + Fore.WHITE + ": " + Fore.MAGENTA + link)
        else:
            print(Fore.BLUE + progress + Fore.WHITE + f" {member_name}")
        
    def save_link(self, link):
        try:
            with open(self.filename, 'a', encoding='utf-8') as f:
                f.write(f"{link}\n")
                f.flush()
        except Exception as e:
            self.log_error(f"Error saving link: {e}")
        
    async def extract_links(self, text):
        if not text:
            return []
        patterns = [
            r'https?://discord\.gg/[A-Za-z0-9]+',
            r'discord\.gg/[A-Za-z0-9]+',
            r'https?://discord\.com/invite/[A-Za-z0-9]+',
            r'discord\.com/invite/[A-Za-z0-9]+'
        ]
        links = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if not match.startswith('http'):
                    match = 'https://' + match
                links.append(match)
        return list(set(links))
    
    async def get_bio_links(self, user):
        try:
            if user.bot:
                return []
            profile = await asyncio.wait_for(user.profile(), timeout=10.0)
            if profile and profile.bio:
                return await self.extract_links(profile.bio)
        except:
            pass
        return []
    
    async def scrape_guild(self, guild_id):
        try:
            self.log_info(f"Attempting to access guild with ID: {guild_id}")
            guild = self.client.get_guild(guild_id)
            
            if not guild:
                self.log_warning("Guild not found in cache, trying to fetch...")
                try:
                    guild = await self.client.fetch_guild(guild_id)
                except discord.Forbidden:
                    self.log_error("Bot doesn't have access to this guild!")
                    self.log_warning("Make sure the bot is added to the server with proper permissions.")
                    return
                except discord.NotFound:
                    self.log_error("Guild not found! Check if the Guild ID is correct.")
                    return
            
            self.log_info(f"Connected to guild: {Fore.CYAN + Style.BRIGHT + guild.name}")
            
            if not guild.chunked:
                self.log_info("Requesting member list...")
                await guild.chunk()
            
            members = [m for m in guild.members if not m.bot]
            self.log_info(f"Members found: {Fore.GREEN + Style.BRIGHT + str(len(members))}")
            
            if len(members) == 0:
                self.log_warning("No members found! Bot might not have member list permissions.")
                self.log_info("Trying alternative member fetching...")
                
            self.log_info(f"Output file: {Fore.YELLOW + Style.BRIGHT + self.filename}")
            print()
            
            with open(self.filename, 'w', encoding='utf-8') as f:
                f.write("")
            
            if len(members) < guild.member_count * 0.7:
                self.log_info("Fetching additional members...")
                try:
                    async for member in guild.fetch_members(limit=None):
                        if not member.bot and member not in members:
                            members.append(member)
                            if len(members) % 100 == 0:
                                self.log_info(f"Fetched {len(members)} members so far...")
                except discord.Forbidden:
                    self.log_warning("Cannot fetch members - insufficient permissions")
                except Exception as e:
                    self.log_warning(f"Error fetching members: {e}")
            
            if len(members) == 0:
                self.log_error("No members available to scan!")
                return
            
            self.log_info(f"Starting to scan {len(members)} members...")
            print(Fore.YELLOW + "-" * 60)
            
            for i, member in enumerate(members, 1):
                try:
                    links = await self.get_bio_links(member)
                    if links:
                        for link in links:
                            if link not in self.links:
                                self.links.add(link)
                                self.save_link(link)
                                self.log_progress(i, len(members), member.name, link)
                    else:
                        self.log_progress(i, len(members), member.name)
                except Exception as e:
                    self.log_warning(f"Error processing {member.name}: {e}")
                
                if i % 10 == 0:
                    await asyncio.sleep(0.5)
            
            print(Fore.YELLOW + "-" * 50)
            print()
            self.log_success(f"Scraping completed!")
            self.log_success(f"Found {Fore.GREEN + Style.BRIGHT + str(len(self.links))} unique links")
            self.log_success(f"Results saved to: {Fore.YELLOW + Style.BRIGHT + self.filename}")
            
        except Exception as e:
            self.log_error(f"Guild scraping failed: {e}")
            import traceback
            self.log_error(f"Traceback: {traceback.format_exc()}")
    
    async def run(self, guild_id):
        @self.client.event
        async def on_ready():
            self.log_success(f"Bot logged in as: {Fore.GREEN + Style.BRIGHT + str(self.client.user)}")
            print()
            await self.scrape_guild(guild_id)
            await self.client.close()
        
        @self.client.event
        async def on_error(event, *args, **kwargs):
            self.log_error(f"Discord event error in {event}: {args}")
        
        try:
            self.log_info("Connecting to Discord...")
            self.log_info("Validating token and permissions...")
            
            await asyncio.wait_for(self.client.start(self.token), timeout=30.0)
            
        except asyncio.TimeoutError:
            self.log_error("Connection timeout! Check your internet connection and token.")
        except discord.LoginFailure:
            self.log_error("Invalid token! Please check your bot token.")
        except discord.HTTPException as e:
            self.log_error(f"HTTP error: {e}")
        except discord.ConnectionClosed:
            self.log_error("Connection was closed by Discord.")
        except Exception as e:
            self.log_error(f"Connection failed: {e}")
            self.log_warning("Common issues:")
            print(Fore.YELLOW + "  • Invalid bot token")
            print(Fore.YELLOW + "  • Bot doesn't have necessary permissions")
            print(Fore.YELLOW + "  • Network connectivity issues")
            print(Fore.YELLOW + "  • Guild ID doesn't exist or bot isn't in that server")

def get_input():
    print(Fore.WHITE + Style.BRIGHT + "Setup Configuration:")
    print(Fore.YELLOW + "-" * 30)
    
    token = sys.argv[1] if len(sys.argv) > 1 else input(
        Fore.CYAN + Style.BRIGHT + "Enter Discord Token: " + Style.RESET_ALL
    ).strip()
    
    if not token:
        print(Fore.RED + Style.BRIGHT + "❌ Token is required!")
        return None, None
    
    try:
        guild_id = int(sys.argv[2]) if len(sys.argv) > 2 else int(input(
            Fore.CYAN + Style.BRIGHT + "Enter Guild ID: " + Style.RESET_ALL
        ).strip())
    except ValueError:
        print(Fore.RED + Style.BRIGHT + "❌ Invalid Guild ID!")
        return None, None
    
    return token, guild_id

def main():
    scraper = Scraper("")
    scraper.clear_screen()
    scraper.show_banner()
    
    token, guild_id = get_input()
    if not token or not guild_id:
        return
    
    scraper.clear_screen()
    scraper.show_banner()
    
    scraper = Scraper(token)
    
    try:
        asyncio.run(scraper.run(guild_id))
    except KeyboardInterrupt:
        print(Fore.YELLOW + Style.BRIGHT + "\n⚠️  Process interrupted by user")
    except Exception as e:
        scraper.log_error(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()
