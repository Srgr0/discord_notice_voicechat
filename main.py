import discord
from discord import app_commands
import json
from datetime import datetime

class MyClient(discord.Client):
    def __init__(self, *args, **kwargs):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.voice_states = True
        super().__init__(intents=intents, *args, **kwargs)
        self.settings_file = 'settings.json'
        self.load_settings()
        self.voice_states = {}
        self.synced = False

    # 設定を読み込む
    def load_settings(self):
        try:
            with open(self.settings_file, 'r') as file:
                self.server_settings = json.load(file)
        except FileNotFoundError:
            self.server_settings = {}

    # 設定を保存する
    def save_settings(self):
        with open(self.settings_file, 'w') as file:
            json.dump(self.server_settings, file, indent=4)

    # サーバー参加時に登録処理を行う
    # システムチャンネルをデフォルトのチャンネルとして設定する
    async def on_guild_join(self, guild):
        system_channel = guild.system_channel
        if system_channel:
            self.server_settings[str(guild.id)] = {'text_channel_id': system_channel.id}
            self.save_settings()
        else:
            print(f"System channel not found in {guild.name}.")

    # ボイスチャットの状況が更新されたら起動する
    async def on_voice_state_update(self, member, before, after):
        # 登録されているサーバーでのみ処理を行う
        guild_id = str(member.guild.id)
        if guild_id in self.server_settings:
            text_channel_id = self.server_settings[guild_id]['text_channel_id']
            channel = self.get_channel(text_channel_id)

            additional_message = self.server_settings[guild_id].get('additional_message', '')

            # 通話開始時のメッセージ
            if before.channel is None and after.channel is not None:
                if len(after.channel.members) == 1:
                    self.voice_states[after.channel.id] = datetime.now()
                    embed = discord.Embed(title="通話開始",
                                        description="ボイスチャットが開始されました。",
                                        color=discord.Color.green())
                    embed.add_field(name="チャンネル", value=after.channel.name)
                    embed.add_field(name="開始時間", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    embed.add_field(name="開始したユーザー", value=member.name)
                    embed.set_footer(text=additional_message)
                    await channel.send(embed=embed)

            # 通話終了時のメッセージ
            if before.channel is not None and after.channel is None:
                if len(before.channel.members) == 0:
                    # 通話開始時刻が記録されていれば、通話時間を計算する
                    # 辞書データが飛ぶ可能性を想定して、継続時間なしのメッセージも用意しておく
                    start_time = self.voice_states.pop(before.channel.id, None)
                    if start_time:
                        duration = datetime.now() - start_time
                        embed = discord.Embed(title="通話終了",
                                            description="ボイスチャットが終了しました。",
                                            color=discord.Color.red())
                        embed.add_field(name="チャンネル", value=before.channel.name)
                        embed.add_field(name="終了時間", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                        embed.add_field(name="継続時間", value=str(duration))
                        embed.set_footer(text=additional_message)
                        await channel.send(embed=embed)
                    else:
                        embed = discord.Embed(title="通話終了",
                                            description="ボイスチャンネルが終了しました。",
                                            color=discord.Color.red())
                        embed.add_field(name="チャンネル", value=before.channel.name)
                        embed.add_field(name="終了時間", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                        embed.set_footer(text=additional_message)
                        await channel.send(embed=embed)

    # 待ち受け処理
    async def on_ready(self):
        if not self.synced:
            await self.tree.sync()  # スラッシュコマンドを同期
            self.synced = True
        print(f"Logged in as {self.user}")

    # チャンネルの変更
    @tree.command(name='set_channel', description='投稿するテキストチャンネルを設定します。')
    async def set_channel(self, ctx, channel_id: int):
        guild_id = str(ctx.guild.id)
        if guild_id in self.server_settings:
            self.server_settings[guild_id]['text_channel_id'] = channel_id
            self.save_settings()
            await ctx.respond(f"テキストチャンネルIDを{channel_id}に設定しました。")
        else:
            await ctx.respond("このサーバーの設定が見つかりません。")

    # メッセージの追加
    @tree.command(name='add_message', description='投稿時に任意のメッセージを追加します。')
    async def add_message(self, ctx, message: str):
        if len(message) > 200:
            await ctx.respond("メッセージは200文字以内にしてください。")
            return

        guild_id = str(ctx.guild.id)
        if guild_id in self.server_settings:
            self.server_settings[guild_id]['additional_message'] = message
            self.save_settings()
            await ctx.respond(f"メッセージを追加しました: {message}")
        else:
            await ctx.respond("このサーバーの設定が見つかりません。")

# 実行
client = MyClient()
client.run('your token here')
