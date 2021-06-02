odoo.define('juragan_fcm_notify.messaging', function (require) {
  const Widget = require('web.Widget');
  const ajax = require('web.ajax');
  const rpc = require('web.rpc');
  const Notification = require('web.Notification');
  let id = 0;

  let Messaging = Widget.extend({
    init: function () {
        this._super.apply(this, arguments);
        this.config = {};
        this.messaging = {};
        this.notifications = {};
    },
    firebase_init: function (user, check_permission = true) {
      let self = this;
      ajax.jsonRpc('/fcm_config').then((config) => {
        self.config = config;
        if (self.config.fcm_active) {
          // Your web app's Firebase configuration
          // For Firebase JS SDK v7.20.0 and later, measurementId is optional
          let firebaseConfig = {
            apiKey: self.config.fcm_api_key,
            authDomain: self.config.fcm_auth_domain,
            projectId: self.config.fcm_project_id,
            storageBucket: self.config.fcm_storage_bucket,
            messagingSenderId: self.config.fcm_messaging_sender_id,
            appId: self.config.fcm_app_id,
            measurementId: self.config.fcm_measurement_id
          };

          // Initialize Firebase
          firebase.initializeApp(firebaseConfig);
          firebase.analytics();

          // Retrieve Firebase Messaging object.
          self.messaging = firebase.messaging();

          if (check_permission) {
            self.check_permission(user);
          }

          // Handle incoming messages. Called when:
          // - a message is received while the app has focus
          // - the user clicks on an app notification created by a service worker
          //   `messaging.onBackgroundMessage` handler.
          self.messaging.onMessage((payload) => {
            self.notify(user, payload);
          });
        }
      });
    },
    check_permission: function (user) {
      let self = this;
      if (self.config.fcm_active) {
        if (!user.fcm_iid_token) {
          self.request_permission(user);
        } else {
          self.get_token(user);
        }
      }
    },
    request_permission: function (user) {
      let self = this;
      swal({
        title: 'Notification Permission Request',
        text: 'We would like to send you notification.\nDo you want to receive notifications from us?',
        icon: 'warning',
        buttons: ["No", "Yes, please!"],
      }).then((value) => {
        if (value) {
          swal({
            text: 'Great! Please click on "Allow" button!',
            button: false
          })
          Notification.requestPermission().then((permission) => {
            if (permission === 'granted') {
              self.get_token(user);
            } else {
              swal({
                title: "We're unable to get permission to notify!",
                text: "Don't worry, we will let you to retry in the next reload.",
                icon: 'error',
                buttons: {
                  cancel: "OK",
                  retry: {
                    text: 'Retry Now',
                    value: true
                  }
                }
              }).then((retry) => {
                if (retry) {
                  window.location.reload();
                }
              });
            }
          })
        }
      })
    },
    get_token: function (user) {
      let self = this;
      // Get registration token. Initially this makes a network call, once retrieved
      // subsequent calls to getToken will return from cache.
      self.messaging.getToken({vapidKey: self.config.fcm_vapid_key}).then((currentToken) => {
        if (currentToken) {
          if (currentToken !== user.fcm_iid_token) {
            self.set_token(user, currentToken).then((success) => {
              if (success) {
                swal({
                  title: 'Notification Permission Request Success',
                  text: "The notification has been activated.",
                  icon: 'success'
                });
              } else {
                swal({
                  title: 'Notification Permission Request Failed',
                  text: "Something wrong happened!",
                  icon: 'error'
                });
              }
            });
          }
        } else {
          self.request_permission(user);
        }
      }).catch((err) => {
        swal({
          title: 'An error occurred while retrieving token.',
          text: err.toString(),
          icon: 'error'
        });
      });
    },
    set_token: function (user, token) {
      let {route, params} = rpc.buildQuery({
        model: 'res.users',
        method: 'write',
        args: [
          [user.id], {'fcm_iid_token': token}
        ]
      });
      return ajax.jsonRpc(route, 'call', params);
    },
    notify: function (user, message) {
      let {notification, data} = message;
      if (!this.$el) {
        this.$el = $('<div class="o_notification_manager"/>');
        this.$el.prependTo('body');
      }
      let NotificationWidget = Notification;
      params = {
        type: data.type,
        sticky: data.sticky === "true",
        title: notification.title,
        message: notification.body,
      }
      let notif = this.notifications[++id] = new NotificationWidget(this, params);
      notif.appendTo(this.$el);
      return id;
    }
  });

  require("web.dom_ready");

  let {route, params} = rpc.buildQuery({
    model: 'res.users',
    method: 'read',
    args: [
      [odoo.session_info.uid], ['fcm_iid_token']
    ]
  });
  ajax.jsonRpc(route, 'call', params).then((result) => {
    let user = result[0]
    let fcm_messaging = new Messaging();
    if (typeof swal !== 'function') {
      ajax.loadJS('/juragan_fcm_notify/static/src/lib/sweetalert.min.js').then(function () {
        fcm_messaging.firebase_init(user);
      });
    } else {
      fcm_messaging.firebase_init(user);
    }
  });

  return Messaging

});