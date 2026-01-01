from utils.router import MainRouter, DbRouter


class OPRouter(MainRouter, DbRouter):
    def get_choices(self):
        return ['Bridge on Unichain (for extra earnings) recommended',
                'start activities (random_route)',
                'Withdraw from OKX (by unwinned)']

    def route(self, task, action):
        return dict(zip(self.get_choices(), [task.unichainbridge,
                                             task.start_activities,
                                             task.withdraw_from_okx]))[action]

    @property
    def action(self):
        self.start_db_router()
        return self.get_action()
