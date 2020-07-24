import json

class Account:

    @staticmethod
    def ToObject(data):
        acc = Account()

        acc.createdAt = data["createdAt"]
        acc.expirationDate = data["expirationDate"]
        acc.monthsInSubscription = data["monthsInSubscription"]
        acc.storageLimit = data["storageLimit"]
        acc.storageUsed = data["storageUsed"]

        return acc


class AccountStatus:

    @staticmethod
    def ToObject(stringObject):
        data = json.loads(stringObject)

        accStatus = AccountStatus()

        accStatus.paymentStatus = data["paymentStatus"]
        accStatus.account = Account.ToObject(data["account"])

        return accStatus

