
import discord
from discord import app_commands
import json
from datetime import datetime

class MyBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.voice_states = True
        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)
        # 早めに登録しないと、反映されない場合がある
        # https://discordpy.readthedocs.io/ja/latest/api.html?highlight=on_ready#discord.on_ready
        self.tree.add_command(app_commands.Command(name='set_channel', description='投稿するテキストチャンネルを設定します。', callback=self.set_channel))
        self.tree.add_command(app_commands.Command(name='add_message', description='投稿時に任意のメッセージを追加します。', callback=self.add_message))
        self.settings_file = 'settings.json'
        self.voice_states = {}
        self.synced = False

        self.load_settings()

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

    # スラッシュコマンドの登録(同期)
    # 接続時(リジュームが失敗して再接続された後を含む)に毎回実行される
    async def on_ready(self):
        if not self.synced:
            await self.tree.sync()
            self.synced = True
        print(f"Logged in as {self.user}")

    # スラッシュコマンドの実行権限をチェックする (管理者のみに制限)
    async def check_admin_permissions(self, interaction: discord.Interaction):
        if interaction.user.guild_permissions.administrator:
            return True
        else:
            await interaction.response.send_message("このコマンドを使用するには管理者権限が必要です。", ephemeral=True)
            return False

    # チャンネルの変更
    async def set_channel(self, interaction: discord.Interaction, channel_id: str):
        if not await self.check_admin_permissions(interaction):
            return
        guild_id = str(interaction.guild_id)
        if guild_id in self.server_settings:
            self.server_settings[guild_id]['text_channel_id'] = channel_id
            self.save_settings()
            await interaction.response.send_message(f"テキストチャンネルIDを{channel_id}に設定しました。")
        else:
            await interaction.response.send_message("このサーバーの設定が見つかりません。")

    # メッセージの追加
    async def add_message(self, interaction: discord.Interaction, message: str):
        if not await self.check_admin_permissions(interaction):
            return
        if len(message) > 200:
            await interaction.response.send_message("メッセージは200文字以内にしてください。")
            return
        guild_id = str(interaction.guild_id)
        if guild_id in self.server_settings:
            self.server_settings[guild_id]['additional_message'] = message
            self.save_settings()
            await interaction.response.send_message(f"追加メッセージを設定しました: {message}")
        else:
            await interaction.response.send_message("このサーバーの設定が見つかりません。")

    # ボイスチャットの状況が更新されたら起動する
    async def on_voice_state_update(self, member, before, after):
        # 登録されているサーバーでのみ処理を行う
        if before.channel != after.channel:
            channel_id = self.server_settings.get(str(member.guild.id), {}).get('text_channel_id')
            additional_message = self.server_settings.get(str(member.guild.id), {}).get('additional_message', '')

            if channel_id:
                channel = member.guild.get_channel(int(channel_id))
                if not channel:
                    return

                # 通話開始時のメッセージ
                if after.channel is not None and len(after.channel.members) == 1:
                    self.voice_states[after.channel.id] = datetime.now()
                    embed = discord.Embed(title="通話開始",
                                          description="ボイスチャットが開始されました。",
                                          color=discord.Color.green())
                    embed.add_field(name="チャンネル", value=after.channel.name)
                    embed.add_field(name="開始時間", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    embed.add_field(name="開始したユーザー", value=member.name)
                    await channel.send(additional_message, embed=embed)

                # 通話終了時のメッセージ
                if before.channel is not None and len(before.channel.members) == 0:
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
                        await channel.send(additional_message, embed=embed)
                    else:
                        embed = discord.Embed(title="通話終了",
                                              description="ボイスチャンネルが終了しました。",
                                              color=discord.Color.red())
                        embed.add_field(name="チャンネル", value=before.channel.name)
                        embed.add_field(name="終了時間", value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                        await channel.send(additional_message, embed=embed)

# 実行
bot = MyBot()
bot.run('your token here')
