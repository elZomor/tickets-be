from django.db import models


class Invitation(models.Model):
    from_member = models.ForeignKey(to='hita.HITAMember', related_name='referrer', on_delete=models.DO_NOTHING)
    invited_member = models.ForeignKey(to='hita.HITAMember', related_name='referred', on_delete=models.DO_NOTHING)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f'{self.from_member.full_name} -> {self.invited_member.full_name}'