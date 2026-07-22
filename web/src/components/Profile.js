import React from 'react';
import { useTranslation } from 'react-i18next';

const Profile = () => {
  const { t } = useTranslation();

  return (
    <div>
      <h1>{t('profile.title')}</h1>
      <p>{t('profile.description')}</p>
      {/* Profile content */}
    </div>
  );
};

export default Profile;