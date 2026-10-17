test('getAttestation retries on IrisRequestError', async () => {
    jest.spyOn(global, 'pollOnce').mockImplementationOnce(() => {
        throw new IrisRequestError();
    }).mockImplementationOnce(() => {
        throw new IrisRequestError();
    }).mockImplementationOnce(() => {
        return { data: 'valid attestation' };
    });

    const result = await getAttestation();
    expect(result).toEqual({ data: 'valid attestation' });
});
