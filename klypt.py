import discord
from discord.ext import commands
from discord import app_commands
from flask import Flask
from threading import Thread
import asyncio
import os

app = Flask('')

@app.route('/')
def home():
    return "OK"

def run():
    app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ============================================================
# CONFIGURATION - ΑΛΛΑΞΕ ΤΑ IDs ΕΔΩ
# ============================================================
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "1495772224236290048"))

# --- ROLE IDs ---
ROLE_DM_ALL = int(os.getenv("ROLE_DM_ALL", "1496228716345294888"))          # Μόνο αυτό το role μπορεί να κάνει !dmall
ROLE_CEO = int(os.getenv("ROLE_CEO", "1496228716345294888"))
ROLE_CO_CEO = int(os.getenv("ROLE_CO_CEO", "1496228907068821794"))
ROLE_MANAGER = int(os.getenv("ROLE_MANAGER", "1496228969089990746"))
ROLE_VERIFIED = int(os.getenv("ROLE_VERIFIED", "1496229353082585149"))       # Auto-role για verification
ROLE_AUTOROLE = int(os.getenv("ROLE_AUTOROLE", "1496229444753428480"))       # Auto-role για νέα μέλη

# --- CHANNEL IDs ---
CHANNEL_TICKETS = int(os.getenv("CHANNEL_TICKETS", "1496236336217067642"))   # Κανάλι για ticket panel
CHANNEL_TICKET_LOGS = int(os.getenv("CHANNEL_TICKET_LOGS", "1496948547508109432"))
CHANNEL_JOIN_LEAVE = int(os.getenv("CHANNEL_JOIN_LEAVE", "1496233884981919784"))
CHANNEL_SECURITY = int(os.getenv("CHANNEL_SECURITY", "1496233938316824657"))
CHANNEL_ROLE_LOGS = int(os.getenv("CHANNEL_ROLE_LOGS", "1496233969513922722"))
CHANNEL_MOD_LOGS = int(os.getenv("CHANNEL_MOD_LOGS", "1496948866057240776"))
CHANNEL_REVIEWS = int(os.getenv("CHANNEL_REVIEWS", "1496237622354378772"))   # Κανάλι για reviews
CHANNEL_VERIFICATION = int(os.getenv("CHANNEL_VERIFICATION", "1496230084946956298"))

# --- TICKET CATEGORY ID ---
TICKET_CATEGORY_ID = int(os.getenv("TICKET_CATEGORY_ID", "1496581309919924365"))

# --- SERVER IMAGE ---
SERVER_IMAGE_URL = os.getenv("SERVER_IMAGE_URL", "https://i.imgur.com/ZGKldpo.png")

# --- TICKET WELCOME MESSAGE (αλλαξε το) ---
TICKET_WELCOME_MESSAGE = os.getenv(
    "TICKET_WELCOME_MESSAGE",
    "👋 Καλωσήρθες στο ticket σου!\n\nΠεριέγραψε το πρόβλημά σου και κάποιος από την ομάδα μας θα σε εξυπηρετήσει σύντομα.\n\n⏳ Χρόνος απόκρισης: εντός 24 ωρών."
)
# ============================================================

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ============================================================
# TICKET VIEWS
# ============================================================

class TicketCategorySelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="🛒 Order", value="order", description="Θέματα παραγγελιών", emoji="🛒"),
            discord.SelectOption(label="🛠️ Support", value="support", description="Τεχνική υποστήριξη", emoji="🛠️"),
            discord.SelectOption(label="❓ Other", value="other", description="Άλλο θέμα", emoji="❓"),
        ]
        super().__init__(
            placeholder="📂 Επίλεξε κατηγορία...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="ticket_category_select"
        )

    async def callback(self, interaction: discord.Interaction):
        category_value = self.values[0]
        category_names = {"order": "Order", "support": "Support", "other": "Other"}
        category_name = category_names[category_value]

        guild = interaction.guild
        member = interaction.user

        # Ελέγχουμε αν υπάρχει ήδη ticket
        for channel in guild.channels:
            if isinstance(channel, discord.TextChannel):
                if channel.topic and f"ticket-{member.id}" in channel.topic:
                    await interaction.response.send_message(
                        f"❌ Έχεις ήδη ανοιχτό ticket: {channel.mention}",
                        ephemeral=True
                    )
                    return

        # Βρίσκουμε την ticket category
        ticket_category = guild.get_channel(TICKET_CATEGORY_ID)

        # Δικαιώματα
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True),
        }

        # Προσθήκη staff roles
        for role_id in [ROLE_CEO, ROLE_CO_CEO, ROLE_MANAGER]:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        emoji_map = {"order": "🛒", "support": "🛠️", "other": "❓"}
        channel_name = f"{emoji_map[category_value]}┃{category_value}-{member.name}"

        ticket_channel = await guild.create_text_channel(
            name=channel_name,
            category=ticket_category,
            overwrites=overwrites,
            topic=f"ticket-{member.id} | Category: {category_name} | Opened by: {member}"
        )

        # Embed μέσα στο ticket
        embed = discord.Embed(
            title=f"{emoji_map[category_value]} Ticket - {category_name}",
            description=TICKET_WELCOME_MESSAGE,
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=SERVER_IMAGE_URL)
        embed.add_field(name="👤 Χρήστης", value=member.mention, inline=True)
        embed.add_field(name="📂 Κατηγορία", value=f"{emoji_map[category_value]} {category_name}", inline=True)
        embed.set_footer(text=f"Ticket ID: {member.id} • Χρησιμοποίησε το κουμπί για να κλείσεις το ticket")

        close_view = CloseTicketView()
        await ticket_channel.send(content=f"{member.mention}", embed=embed, view=close_view)

        await interaction.response.send_message(
            f"✅ Το ticket σου δημιουργήθηκε: {ticket_channel.mention}",
            ephemeral=True
        )

        # Log
        log_ch = guild.get_channel(CHANNEL_TICKET_LOGS)
        if log_ch:
            log_embed = discord.Embed(
                title="🎫 Νέο Ticket Ανοίχτηκε",
                color=discord.Color.green()
            )
            log_embed.add_field(name="Χρήστης", value=f"{member} ({member.id})", inline=True)
            log_embed.add_field(name="Κατηγορία", value=category_name, inline=True)
            log_embed.add_field(name="Κανάλι", value=ticket_channel.mention, inline=True)
            await log_ch.send(embed=log_embed)


class TicketCategoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketCategorySelect())


class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Close Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        guild = interaction.guild
        member = interaction.user

        # Ελέγχουμε αν είναι staff ή ο ιδιοκτήτης
        is_staff = any(r.id in [ROLE_CEO, ROLE_CO_CEO, ROLE_MANAGER] for r in member.roles)
        is_owner = channel.topic and f"ticket-{member.id}" in channel.topic

        if not (is_staff or is_owner):
            await interaction.response.send_message("❌ Δεν έχεις δικαίωμα να κλείσεις αυτό το ticket.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🔒 Κλείσιμο Ticket",
            description=f"Το ticket κλείνει σε 5 δευτερόλεπτα...\nΚλείστηκε από: {member.mention}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)

        # Log
        log_ch = guild.get_channel(CHANNEL_TICKET_LOGS)
        if log_ch:
            log_embed = discord.Embed(
                title="🔒 Ticket Έκλεισε",
                color=discord.Color.red()
            )
            log_embed.add_field(name="Κανάλι", value=channel.name, inline=True)
            log_embed.add_field(name="Έκλεισε από", value=f"{member} ({member.id})", inline=True)
            await log_ch.send(embed=log_embed)

        await asyncio.sleep(5)
        await channel.delete()


# ============================================================
# VERIFICATION VIEW
# ============================================================

class VerificationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Verify", style=discord.ButtonStyle.success, custom_id="verify_btn", emoji="✅")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.user
        guild = interaction.guild
        role = guild.get_role(ROLE_VERIFIED)

        if role in member.roles:
            await interaction.response.send_message("✅ Είσαι ήδη verified!", ephemeral=True)
            return

        await member.add_roles(role)
        await interaction.response.send_message(
            f"🎉 Επαληθεύτηκες επιτυχώς! Καλωσήρθες στον server, {member.mention}!",
            ephemeral=True
        )


# ============================================================
# REVIEW VIEW
# ============================================================

class ReviewStarsSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="⭐ 1 Αστέρι", value="1", emoji="⭐"),
            discord.SelectOption(label="⭐⭐ 2 Αστέρια", value="2", emoji="⭐"),
            discord.SelectOption(label="⭐⭐⭐ 3 Αστέρια", value="3", emoji="⭐"),
            discord.SelectOption(label="⭐⭐⭐⭐ 4 Αστέρια", value="4", emoji="⭐"),
            discord.SelectOption(label="⭐⭐⭐⭐⭐ 5 Αστέρια", value="5", emoji="⭐"),
        ]
        super().__init__(placeholder="⭐ Επίλεξε βαθμολογία...", options=options, custom_id="review_stars")

    async def callback(self, interaction: discord.Interaction):
        stars = int(self.values[0])
        modal = ReviewModal(stars)
        await interaction.response.send_modal(modal)


class ReviewModal(discord.ui.Modal, title="✍️ Γράψε το Review σου"):
    comment = discord.ui.TextInput(
        label="Σχόλιο",
        placeholder="Γράψε το σχόλιο σου εδώ...",
        style=discord.TextStyle.long,
        max_length=500,
        required=True
    )

    def __init__(self, stars: int):
        super().__init__()
        self.stars = stars

    async def on_submit(self, interaction: discord.Interaction):
        star_display = "⭐" * self.stars + "☆" * (5 - self.stars)
        member = interaction.user

        review_channel = interaction.guild.get_channel(CHANNEL_REVIEWS)
        if not review_channel:
            await interaction.response.send_message("❌ Δεν βρέθηκε το κανάλι reviews.", ephemeral=True)
            return

        embed = discord.Embed(
            title="📝 Νέο Review",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=SERVER_IMAGE_URL)
        embed.add_field(name="👤 Χρήστης", value=f"{member.mention} ({member})", inline=False)
        embed.add_field(name="⭐ Βαθμολογία", value=f"{star_display} ({self.stars}/5)", inline=False)
        embed.add_field(name="💬 Σχόλιο", value=self.comment.value, inline=False)
        embed.set_footer(text=f"ID: {member.id}")

        await review_channel.send(embed=embed)
        await interaction.response.send_message("✅ Το review σου στάλθηκε! Ευχαριστούμε! 🙏", ephemeral=True)


class ReviewView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(ReviewStarsSelect())


# ============================================================
# BOT EVENTS
# ============================================================

@bot.event
async def on_ready():
    print(f"✅ Bot συνδέθηκε ως {bot.user}")
    bot.add_view(TicketCategoryView())
    bot.add_view(CloseTicketView())
    bot.add_view(VerificationView())
    bot.add_view(ReviewView())
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"❌ Sync error: {e}")


@bot.event
async def on_member_join(member: discord.Member):
    guild = member.guild

    # Auto-role
    autorole = guild.get_role(ROLE_AUTOROLE)
    if autorole:
        try:
            await member.add_roles(autorole)
        except:
            pass

    # Join log
    log_ch = guild.get_channel(CHANNEL_JOIN_LEAVE)
    if log_ch:
        embed = discord.Embed(
            title="📥 Νέο Μέλος Εντάχθηκε",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="👤 Χρήστης", value=f"{member.mention} ({member})", inline=True)
        embed.add_field(name="🆔 ID", value=str(member.id), inline=True)
        embed.add_field(name="📅 Λογαριασμός δημιουργήθηκε", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=False)
        embed.set_footer(text=f"Σύνολο μελών: {guild.member_count}")
        await log_ch.send(embed=embed)


@bot.event
async def on_member_remove(member: discord.Member):
    log_ch = member.guild.get_channel(CHANNEL_JOIN_LEAVE)
    if log_ch:
        embed = discord.Embed(
            title="📤 Μέλος Αποχώρησε",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="👤 Χρήστης", value=f"{member} ({member.id})", inline=True)
        embed.add_field(name="📅 Εντάχθηκε", value=f"<t:{int(member.joined_at.timestamp())}:R>" if member.joined_at else "Άγνωστο", inline=True)
        embed.set_footer(text=f"Σύνολο μελών: {member.guild.member_count}")
        await log_ch.send(embed=embed)


@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    # Role logs
    if before.roles != after.roles:
        added = [r for r in after.roles if r not in before.roles]
        removed = [r for r in before.roles if r not in after.roles]

        log_ch = after.guild.get_channel(CHANNEL_ROLE_LOGS)
        if log_ch:
            if added:
                embed = discord.Embed(title="🟢 Role Προστέθηκε", color=discord.Color.green())
                embed.add_field(name="Χρήστης", value=f"{after.mention} ({after})", inline=True)
                embed.add_field(name="Role", value=", ".join([r.mention for r in added]), inline=True)
                await log_ch.send(embed=embed)
            if removed:
                embed = discord.Embed(title="🔴 Role Αφαιρέθηκε", color=discord.Color.red())
                embed.add_field(name="Χρήστης", value=f"{after.mention} ({after})", inline=True)
                embed.add_field(name="Role", value=", ".join([r.mention for r in removed]), inline=True)
                await log_ch.send(embed=embed)


@bot.event
async def on_guild_role_create(role: discord.Role):
    log_ch = role.guild.get_channel(CHANNEL_ROLE_LOGS)
    if log_ch:
        embed = discord.Embed(title="✨ Νέο Role Δημιουργήθηκε", color=discord.Color.blue())
        embed.add_field(name="Role", value=f"{role.mention} ({role.name})", inline=True)
        embed.add_field(name="ID", value=str(role.id), inline=True)
        await log_ch.send(embed=embed)


@bot.event
async def on_guild_role_delete(role: discord.Role):
    log_ch = role.guild.get_channel(CHANNEL_ROLE_LOGS)
    if log_ch:
        embed = discord.Embed(title="🗑️ Role Διαγράφηκε", color=discord.Color.red())
        embed.add_field(name="Role", value=role.name, inline=True)
        embed.add_field(name="ID", value=str(role.id), inline=True)
        await log_ch.send(embed=embed)


@bot.event
async def on_member_ban(guild: discord.Guild, user: discord.User):
    log_ch = guild.get_channel(CHANNEL_MOD_LOGS)
    if log_ch:
        embed = discord.Embed(title="🔨 Χρήστης Μπανάρηκε", color=discord.Color.dark_red())
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Χρήστης", value=f"{user} ({user.id})", inline=True)
        await log_ch.send(embed=embed)


@bot.event
async def on_member_unban(guild: discord.Guild, user: discord.User):
    log_ch = guild.get_channel(CHANNEL_MOD_LOGS)
    if log_ch:
        embed = discord.Embed(title="✅ Χρήστης Ξεμπανάρηκε", color=discord.Color.green())
        embed.set_thumbnail(url=user.display_avatar.url)
        embed.add_field(name="Χρήστης", value=f"{user} ({user.id})", inline=True)
        await log_ch.send(embed=embed)


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # Security: Discord link detection
    import re
    discord_link_pattern = re.compile(
        r"(https?://)?(www\.)?(discord\.(gg|io|me|li|com/invite))/[a-zA-Z0-9]+"
    )

    if discord_link_pattern.search(message.content):
        # Ελέγχουμε αν έχει δικαίωμα
        allowed_roles = [ROLE_CEO, ROLE_CO_CEO, ROLE_MANAGER, ROLE_DM_ALL]
        if not any(r.id in allowed_roles for r in message.author.roles):
            try:
                await message.delete()
                # Timeout 1 ώρα
                import datetime
                await message.author.timeout(
                    datetime.timedelta(hours=1),
                    reason="Αποστολή Discord invite link χωρίς άδεια"
                )
                warn_msg = await message.channel.send(
                    f"⚠️ {message.author.mention} Τα Discord links δεν επιτρέπονται! Έχεις λάβει timeout 1 ώρας."
                )
                await asyncio.sleep(5)
                await warn_msg.delete()

                # Security log
                log_ch = message.guild.get_channel(CHANNEL_SECURITY)
                if log_ch:
                    embed = discord.Embed(
                        title="🔒 Discord Link Εντοπίστηκε",
                        color=discord.Color.orange()
                    )
                    embed.add_field(name="Χρήστης", value=f"{message.author.mention} ({message.author})", inline=True)
                    embed.add_field(name="Κανάλι", value=message.channel.mention, inline=True)
                    embed.add_field(name="Μήνυμα", value=message.content[:200], inline=False)
                    embed.add_field(name="Ποινή", value="⏱️ Timeout 1 ώρα", inline=True)
                    await log_ch.send(embed=embed)

                # Mod log για timeout
                mod_log = message.guild.get_channel(CHANNEL_MOD_LOGS)
                if mod_log:
                    embed = discord.Embed(title="⏱️ Timeout Δόθηκε (Auto)", color=discord.Color.orange())
                    embed.add_field(name="Χρήστης", value=f"{message.author} ({message.author.id})", inline=True)
                    embed.add_field(name="Διάρκεια", value="1 ώρα", inline=True)
                    embed.add_field(name="Λόγος", value="Discord invite link", inline=True)
                    await mod_log.send(embed=embed)
            except discord.Forbidden:
                pass

    await bot.process_commands(message)


# ============================================================
# COMMANDS
# ============================================================

@bot.command(name="dmall")
async def dmall(ctx, *, message: str):
    """Στέλνει DM σε όλα τα μέλη - μόνο για συγκεκριμένο role"""
    if not any(r.id == ROLE_DM_ALL for r in ctx.author.roles):
        await ctx.send("❌ Δεν έχεις άδεια να χρησιμοποιήσεις αυτή την εντολή.", delete_after=5)
        return

    await ctx.send("📨 Αποστολή DM σε όλα τα μέλη...", delete_after=3)
    success = 0
    failed = 0

    for member in ctx.guild.members:
        if not member.bot:
            try:
                await member.send(message)
                success += 1
                await asyncio.sleep(0.5)
            except:
                failed += 1

    await ctx.send(f"✅ DM στάλθηκε! Επιτυχία: {success} | Αποτυχία: {failed}", delete_after=10)


@bot.command(name="setup_tickets")
@commands.has_permissions(administrator=True)
async def setup_tickets(ctx):
    """Δημιουργεί το ticket panel"""
    channel = ctx.guild.get_channel(CHANNEL_TICKETS)
    if not channel:
        channel = ctx.channel

    embed = discord.Embed(
        title="🎫 Σύστημα Tickets",
        description=(
            "**Καλωσήρθες στο σύστημα υποστήριξης!**\n\n"
            "Επίλεξε μια κατηγορία από το dropdown menu παρακάτω για να ανοίξεις ένα ticket.\n\n"
            "🛒 **Order** — Θέματα παραγγελιών\n"
            "🛠️ **Support** — Τεχνική υποστήριξη\n"
            "❓ **Other** — Οτιδήποτε άλλο\n\n"
            "⚠️ *Παρακαλώ μην ανοίγεις ticket χωρίς λόγο.*"
        ),
        color=discord.Color.blue()
    )
    embed.set_image(url=SERVER_IMAGE_URL)
    embed.set_footer(text="Ticket System • Η ομάδα μας είναι εδώ για σένα!")

    view = TicketCategoryView()
    await channel.send(embed=embed, view=view)
    await ctx.send("✅ Ticket panel δημιουργήθηκε!", delete_after=3)


@bot.command(name="setup_verification")
@commands.has_permissions(administrator=True)
async def setup_verification(ctx):
    """Δημιουργεί το verification panel"""
    channel = ctx.guild.get_channel(CHANNEL_VERIFICATION)
    if not channel:
        channel = ctx.channel

    embed = discord.Embed(
        title="🔐 Verification",
        description=(
            "**Καλωσήρθες στον server!** 👋\n\n"
            "Για να αποκτήσεις πρόσβαση σε όλα τα κανάλια, πάτησε το κουμπί παρακάτω.\n\n"
            "✅ Πάτησε **Verify** για να επαληθευτείς!"
        ),
        color=discord.Color.green()
    )
    embed.set_image(url=SERVER_IMAGE_URL)
    embed.set_footer(text="Verification System")

    view = VerificationView()
    await channel.send(embed=embed, view=view)
    await ctx.send("✅ Verification panel δημιουργήθηκε!", delete_after=3)


@bot.command(name="setup_review")
@commands.has_permissions(administrator=True)
async def setup_review(ctx):
    """Δημιουργεί το review panel"""
    embed = discord.Embed(
        title="⭐ Κάνε Review",
        description=(
            "**Θέλεις να μοιραστείς την εμπειρία σου;** 📝\n\n"
            "Επίλεξε βαθμολογία από το dropdown και γράψε το σχόλιό σου!\n\n"
            "Τα reviews μας βοηθούν να βελτιωνόμαστε συνεχώς. 🙏"
        ),
        color=discord.Color.gold()
    )
    embed.set_image(url=SERVER_IMAGE_URL)
    embed.set_footer(text="Review System")

    view = ReviewView()
    await ctx.send(embed=embed, view=view)
    await ctx.message.delete()


@bot.command(name="timeout")
@commands.has_permissions(moderate_members=True)
async def manual_timeout(ctx, member: discord.Member, minutes: int, *, reason: str = "Κανένας λόγος"):
    import datetime
    await member.timeout(datetime.timedelta(minutes=minutes), reason=reason)
    await ctx.send(f"⏱️ {member.mention} έλαβε timeout {minutes} λεπτά. Λόγος: {reason}")

    log_ch = ctx.guild.get_channel(CHANNEL_MOD_LOGS)
    if log_ch:
        embed = discord.Embed(title="⏱️ Timeout Δόθηκε", color=discord.Color.orange())
        embed.add_field(name="Χρήστης", value=f"{member} ({member.id})", inline=True)
        embed.add_field(name="Moderator", value=f"{ctx.author}", inline=True)
        embed.add_field(name="Διάρκεια", value=f"{minutes} λεπτά", inline=True)
        embed.add_field(name="Λόγος", value=reason, inline=False)
        await log_ch.send(embed=embed)


@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason: str = "Κανένας λόγος"):
    await member.ban(reason=reason)
    await ctx.send(f"🔨 {member} Banned. Λόγος: {reason}")

    log_ch = ctx.guild.get_channel(CHANNEL_MOD_LOGS)
    if log_ch:
        embed = discord.Embed(title="🔨 Ban", color=discord.Color.dark_red())
        embed.add_field(name="Χρήστης", value=f"{member} ({member.id})", inline=True)
        embed.add_field(name="Moderator", value=f"{ctx.author}", inline=True)
        embed.add_field(name="Λόγος", value=reason, inline=False)
        await log_ch.send(embed=embed)


@bot.command(name="unban")
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int, *, reason: str = "Κανένας λόγος"):
    user = await bot.fetch_user(user_id)
    await ctx.guild.unban(user, reason=reason)
    await ctx.send(f"✅ {user} Unbanned.")

    log_ch = ctx.guild.get_channel(CHANNEL_MOD_LOGS)
    if log_ch:
        embed = discord.Embed(title="✅ Unban", color=discord.Color.green())
        embed.add_field(name="Χρήστης", value=f"{user} ({user.id})", inline=True)
        embed.add_field(name="Moderator", value=f"{ctx.author}", inline=True)
        embed.add_field(name="Λόγος", value=reason, inline=False)
        await log_ch.send(embed=embed)


if __name__ == "__main__":
    bot.run(TOKEN)
