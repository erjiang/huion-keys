class Update: 
  
  subscribers=[]

  def send(self, msg):
    for subscriber in self.subscribers:
      subscriber(msg)
  
  def subscribe(self, cb):
    self.subscribers.append(cb)

  def unsubscribe(self, cb):
    self.subscribers.remove(cb)
