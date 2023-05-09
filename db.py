import sqlite3

class BotDB:

    def __init__(self, db_file):
        self.conn = sqlite3.connect(db_file)
        self.cursor = self.conn.cursor()

    def user_exists(self, user_id):
        """Проверяем, есть ли юзер в базе"""
        result = self.cursor.execute("SELECT `id` FROM `balance` WHERE `user_id` = ?", (user_id,))
        return bool(len(result.fetchall()))

    def get_user_id(self, user_id):
        """Достаем id юзера в базе по его user_id"""
        result = self.cursor.execute("SELECT `id` FROM `balance` WHERE `user_id` = ?", (user_id,))
        balance = self.cursor.execute("SELECT `id` FROM `balance` WHERE `user_id` = ?", (user_id,))
        return result.fetchone()[0]

    def add_user(self, user_id):
        """Добавляем юзера в базу"""
        self.cursor.execute("INSERT INTO `balance` (`user_id`) VALUES (?)", (user_id,))
        return self.conn.commit()

    def get_balance(self, user_id):
        """Получаем баланс юзера"""
        balance = self.cursor.execute("SELECT balance FROM balance WHERE user_id = (?) ",(user_id,))
        return balance.fetchone()[0]

    def update_balance(self, user_id, upd_balance):
        """Заменяем значение балланса"""
        self.cursor.execute("UPDATE balance SET balance = (?) WHERE user_id = (?) ",(upd_balance,user_id))
        return self.conn.commit()

    def get_user_buy(self,id):
        """Получаем аккаунт для передачи киенту"""
        account = self.cursor.execute("SELECT * FROM accounts WHERE id = (?) ",(id,))
        return account.fetchone()


    def close(self):
        """Закрываем соединение с БД"""
        self.connection.close()
