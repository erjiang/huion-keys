class Update: 
  
  subscribers=[]

  def send(self, msg):
    for subscriber in self.subscribers:
      subscriber(msg)
  
  def subscribe(self, cb):
    self.subscribers.append(cb)
    print(self.subscribers)

  def unsubscribe(self, cb):
    print(cb)
    print(self.subscribers)
    self.subscribers.remove(cb)
    print(self.subscribers)