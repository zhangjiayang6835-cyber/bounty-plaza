import React from 'react';
import { useTranslation } from 'react-i18next';

const BountyList = () => {
  const { t } = useTranslation();

  return (
    <div>
      <h1>{t('bounty.title')}</h1>
      <p>{t('bounty.description')}</p>
      {/* Bounty list content */}
    </div>
  );
};

export default BountyList;