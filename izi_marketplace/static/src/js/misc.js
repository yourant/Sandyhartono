odoo.define('izi_marketplace.framework', function (require) {
  "use strict";

  let core = require('web.core');
  let framework = require('web.framework');
  let AbstractAction = require('web.AbstractAction');
  let ControlPanelMixin = require('web.ControlPanelMixin');
  let originblockUI = framework.blockUI;
  let originUnblockUI = framework.unblockUI;

  let CloseNotificationAction = AbstractAction.extend(ControlPanelMixin, {
    init: function (parent, action) {
      this.actionManager = parent;
      this.action = action;
      this.originalUrl = window.location.href;
      return this._super.apply(this, arguments);
    },
    start: function () {
      let self = this;
      return this._super.apply(this, arguments).then(function () {
        let actionManager = self.actionManager;
        let action = self.action;
        // let controller = parent.getCurrentController()
        let params = action.params || {};
        self.closeNotifications(params);
        if (action.context.close_notifications_and_wizard) {
          actionManager.do_action({'type': 'ir.actions.act_window_close'});
        }
      });
    },
    closeNotifications: function (params) {
      if (window.location.href !== this.originalUrl) {
        window.location = this.originalUrl;
      }
      let self = this;
      if (!params) {
        params = {}
      }
      let $notifs = $('.o_notification .o_close');
      if ($notifs.length > 0) {
        if (!params.force_show_number || params.close_on_finish) {
          setTimeout(function () {
            let $notif = [].shift.call($notifs);
            if ($notif) {
              $notif.click();
            }
            self.closeNotifications(params);
          }, 500);
        } else if ($notifs.length > params.force_show_number) {
          setTimeout(function () {
            let $notifs_to_close = $notifs.slice(0, $notifs.length - params.force_show_number);
            if ($notifs_to_close) {
              $notifs_to_close.click();
            }
            self.closeNotifications(params);
          }, 500);
        } else if ($notifs.length <= params.force_show_number) {
          setTimeout(function () {
            if (!params.hasOwnProperty('close_on_finish')) {
              params.close_on_finish = true;
            }
            self.closeNotifications(params);
          }, 500);
        } else {
          setTimeout(function () {
            self.closeNotifications(params);
          }, 500);
        }
      }
    }
  });

  framework.blockUI = function () {
    new CloseNotificationAction().closeNotifications({force_show_number: 1, close_on_finish: false});
    return originblockUI();
  }

  framework.unblockUI = function () {
    new CloseNotificationAction().closeNotifications();
    return originUnblockUI();
  }

  core.action_registry.add('close_notifications', CloseNotificationAction);
});