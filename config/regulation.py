class Regulation:
    def __init__(
        self,
        num_players,
        num_wolves,
        num_fortunetellers,
        num_knights,
        num_mediums,
        num_hunters,
        num_freemasons,
        has_audience,
    ):
        self.num_players = num_players
        self.num_wolves = num_wolves
        self.num_fortunetellers = num_fortunetellers
        self.num_knights = num_knights
        self.num_mediums = num_mediums
        self.num_hunters = num_hunters
        self.num_freemasons = num_freemasons
        self.has_audience = has_audience

    def __repr__(self):
        return f"<Regulation players={self.num_players}>"

    def some_method(self):
        return "This is a method in the Regulation class."
